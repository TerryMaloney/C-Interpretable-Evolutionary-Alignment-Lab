/**
 * Client-side Convergence Score computation using DuckDB-WASM.
 *
 * The C-Score quantifies how many independent data streams agree that a
 * geographic point is anomalous, after correcting for known confounders.
 *
 * Formula:
 *   C_raw = Σ(layers within haversine radius R) × tier_weight
 *   C_pop = C_raw × population_correction
 *   C_mask = C_pop × military_mask_factor
 *   C_score = C_mask × solar_weight × industrial_correction
 *
 * Tier weights: T1=1.0, T2=0.5, T3=0.25
 * Control layers (space_weather, adsb_traffic, nighttime_lights, faa_airspace)
 * are excluded from the sum and used only as penalty multipliers.
 */

// ── Tier weights ───────────────────────────────────────────────────────────────
const TIER_WEIGHTS = { 1: 1.0, 2: 0.5, 3: 0.25 };

// ── Control layer exclusions and penalties ────────────────────────────────────
const CONTROL_LAYERS = new Set([
  'space_weather', 'adsb_traffic', 'nighttime_lights', 'faa_airspace',
]);

const MILITARY_PENALTY = 0.4;    // if co-located with FAA SUA
const SOLAR_HIGH_KP = 5.0;       // Kp threshold for solar penalty
const SOLAR_PENALTY = 0.6;       // multiplier when Kp >= threshold
const INDUSTRIAL_PENALTY = 0.7;  // multiplier if inside nighttime light zone

// ── Haversine distance ─────────────────────────────────────────────────────────
export function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const dPhi = ((lat2 - lat1) * Math.PI) / 180;
  const dLam = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dPhi / 2) ** 2 +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(dLam / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Compute C-Score for a query point against all loaded layer data.
 *
 * @param {number} lat - Query latitude
 * @param {number} lon - Query longitude
 * @param {Object} layerData - { layerName: GeoJSON FeatureCollection }
 * @param {Object} registry - layer_registry.json content
 * @param {number} radiusKm - co-location radius (default 50km)
 * @param {Object} options - { hideMilitary, hideSolar, hideIndustrial }
 * @returns {Object} { cScore, rawScore, layers, breakdown, penalties }
 */
export function computeCScore(lat, lon, layerData, registry, radiusKm = 50, options = {}) {
  const registryLayers = registry?.layers || {};
  const layers = [];
  let rawScore = 0;

  let militaryPenalty = 1.0;
  let solarPenalty = 1.0;
  let industrialPenalty = 1.0;

  for (const [layerName, geoJson] of Object.entries(layerData)) {
    const features = geoJson?.features || [];
    if (!features.length) continue;

    const meta = registryLayers[layerName] || {};
    const tier = meta.tier ?? 3;
    const weight = TIER_WEIGHTS[tier] ?? 0.25;

    // Handle control layers separately
    if (CONTROL_LAYERS.has(layerName)) {
      if (layerName === 'faa_airspace') {
        const hit = features.some(f => {
          const coords = f.geometry?.coordinates;
          if (!coords) return false;
          const [fLon, fLat] = coords;
          return haversineKm(lat, lon, fLat, fLon) < radiusKm;
        });
        if (hit) militaryPenalty = 1 - MILITARY_PENALTY;
      }

      if (layerName === 'space_weather') {
        const hasHighKp = features.some(f => {
          const kp = f.properties?.extra?.kp_index ?? f.properties?.kp_index;
          return kp != null && parseFloat(kp) >= SOLAR_HIGH_KP;
        });
        if (hasHighKp) solarPenalty = SOLAR_PENALTY;
      }

      if (layerName === 'nighttime_lights') {
        const hit = features.some(f => {
          const coords = f.geometry?.coordinates;
          if (!coords) return false;
          const [fLon, fLat] = coords;
          return haversineKm(lat, lon, fLat, fLon) < radiusKm;
        });
        if (hit) industrialPenalty = INDUSTRIAL_PENALTY;
      }
      continue;
    }

    // Signal layer: count records within radius
    let hitCount = 0;
    for (const f of features) {
      const coords = f.geometry?.coordinates;
      if (!coords || coords.length < 2) continue;
      const [fLon, fLat] = coords;
      if (haversineKm(lat, lon, fLat, fLon) <= radiusKm) {
        hitCount++;
      }
    }

    if (hitCount > 0) {
      const contribution = weight;
      rawScore += contribution;
      layers.push({
        name: layerName,
        label: meta.name || layerName,
        tier,
        weight,
        hitCount,
        contribution,
        category: meta.category,
      });
    }
  }

  const penaltyFactor = militaryPenalty * solarPenalty * industrialPenalty;
  const cScore = Math.min(10, rawScore * penaltyFactor);

  return {
    cScore: Math.round(cScore * 100) / 100,
    rawScore: Math.round(rawScore * 100) / 100,
    layerCount: layers.length,
    layers: layers.sort((a, b) => b.contribution - a.contribution),
    penalties: {
      military: militaryPenalty < 1,
      militaryFactor: militaryPenalty,
      solar: solarPenalty < 1,
      solarFactor: solarPenalty,
      industrial: industrialPenalty < 1,
      industrialFactor: industrialPenalty,
    },
  };
}

/**
 * Compute C-Scores for a grid of cells over a bounding box.
 * Returns array of { lat, lon, cScore, layerCount } sorted descending by cScore.
 *
 * This runs in-browser — suitable for small grids (<5000 cells).
 * For larger grids, use the Python convergence_score.py.
 */
export function computeGridScores(bbox, step, layerData, registry, radiusKm = 50) {
  const { latMin, latMax, lonMin, lonMax } = bbox;
  const cells = [];

  for (let lat = latMin + step / 2; lat <= latMax; lat += step) {
    for (let lon = lonMin + step / 2; lon <= lonMax; lon += step) {
      const result = computeCScore(
        Math.round(lat * 1000) / 1000,
        Math.round(lon * 1000) / 1000,
        layerData, registry, radiusKm
      );
      if (result.cScore > 0) {
        cells.push({
          lat: Math.round(lat * 1000) / 1000,
          lon: Math.round(lon * 1000) / 1000,
          ...result,
        });
      }
    }
  }

  return cells.sort((a, b) => b.cScore - a.cScore);
}

/**
 * C-Score interpretation label
 */
export function cScoreLabel(score) {
  if (score >= 8) return { label: 'CRITICAL', color: '#ff2244' };
  if (score >= 6) return { label: 'HIGH', color: '#ff6644' };
  if (score >= 4) return { label: 'ELEVATED', color: '#ffaa00' };
  if (score >= 2) return { label: 'MODERATE', color: '#88cc44' };
  if (score > 0)  return { label: 'LOW', color: '#4488ff' };
  return { label: 'NONE', color: '#606078' };
}

/**
 * DuckDB-WASM powered C-Score computation for large datasets.
 * Falls back to JS implementation when DB not available.
 */
export async function computeCScoreWithDuckDB(lat, lon, db, radiusKm = 50) {
  if (!db) {
    console.warn('DuckDB not initialized — using JS fallback');
    return null;
  }

  try {
    const conn = await db.connect();
    // Query pre-loaded Arrow tables for fast haversine filtering
    const result = await conn.query(`
      SELECT
        layer,
        COUNT(*) as hit_count,
        AVG(confidence) as avg_confidence
      FROM events
      WHERE (
        2 * 6371 * ASIN(SQRT(
          SIN(RADIANS(lat - ${lat}) / 2) * SIN(RADIANS(lat - ${lat}) / 2) +
          COS(RADIANS(${lat})) * COS(RADIANS(lat)) *
          SIN(RADIANS(lon - ${lon}) / 2) * SIN(RADIANS(lon - ${lon}) / 2)
        ))
      ) <= ${radiusKm}
      GROUP BY layer
      ORDER BY hit_count DESC
    `);
    await conn.close();
    return result.toArray();
  } catch (err) {
    console.error('DuckDB query failed:', err);
    return null;
  }
}

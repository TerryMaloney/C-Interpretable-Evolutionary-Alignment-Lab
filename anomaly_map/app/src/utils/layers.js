// Layer metadata and color utilities

export const CATEGORY_COLORS = {
  uap: [255, 80, 80],
  marine: [0, 160, 255],
  geophysical: [80, 160, 255],
  em_disturbance: [200, 100, 255],
  radiation: [255, 200, 0],
  thermal: [255, 120, 0],
  ionospheric: [120, 200, 255],
  atmospheric: [100, 220, 180],
  acoustic: [255, 180, 80],
  biological: [80, 220, 120],
  subsurface: [160, 120, 80],
  anomaly_report: [255, 60, 100],
  em_field: [180, 100, 255],
  aviation_control: [100, 100, 120],
  solar_control: [255, 200, 80],
  mask: [80, 80, 100],
  infrastructure: [200, 160, 80],
  historical: [180, 160, 140],
  earth_lights: [255, 240, 120],
  nav_disruption: [100, 200, 160],
  ocean: [40, 120, 200],
  unknown: [150, 150, 150],
};

export const CONFIDENCE_RADIUS = {
  5: 8,
  4: 6,
  3: 5,
  2: 4,
  1: 3,
};

export function getCategoryColor(category) {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.unknown;
}

export function getConfidenceRadius(confidence) {
  return CONFIDENCE_RADIUS[confidence] || 4;
}

export function getLayerColor(layerName, registry) {
  const meta = registry?.layers?.[layerName];
  if (!meta) return [150, 150, 150];
  return getCategoryColor(meta.category);
}

// Build flat list of all features across loaded layers
export function buildFlatFeatures(layerData, visibleLayers, registry) {
  const features = [];
  for (const layerName of visibleLayers) {
    const data = layerData[layerName];
    if (!data?.features) continue;
    const meta = registry?.layers?.[layerName] || {};
    const color = getCategoryColor(meta.category);
    for (const f of data.features) {
      const coords = f.geometry?.coordinates;
      if (!coords || coords.length < 2) continue;
      features.push({
        position: [coords[0], coords[1]],
        color,
        layer: layerName,
        properties: f.properties,
        radius: getConfidenceRadius(f.properties?.confidence),
      });
    }
  }
  return features;
}

// Color scale for C-Score heatmap (cool → hot)
export function cScoreToColor(score, maxScore = 10) {
  const t = Math.min(1, score / maxScore);
  // Blue → cyan → green → yellow → red
  if (t < 0.25) {
    const s = t / 0.25;
    return [0, Math.round(s * 180), 255, Math.round(t * 2 * 255)];
  } else if (t < 0.5) {
    const s = (t - 0.25) / 0.25;
    return [0, Math.round(180 + s * 75), Math.round(255 - s * 255), 180];
  } else if (t < 0.75) {
    const s = (t - 0.5) / 0.25;
    return [Math.round(s * 255), 255, 0, 200];
  } else {
    const s = (t - 0.75) / 0.25;
    return [255, Math.round(255 - s * 200), 0, 220];
  }
}

// Color for an alignment line. Significant (low p) renders hot + bold; chance-level
// alignments render faint + washed-out — so an honestly-debunked "ley line" literally
// looks unconvincing on the map.
export function alignmentColor(pValue = 1, significant = false) {
  const strength = Math.max(0, Math.min(1, 1 - pValue));  // 0 = chance, 1 = strong signal
  if (significant) {
    return [255, Math.round(140 - strength * 140), 30, 235];   // orange → red, bold
  }
  return [120, 160, 180, 70];                                  // faint blue-grey
}

// Pixel width for an alignment line, scaled by member count.
export function alignmentWidth(pointCount = 0) {
  return Math.min(9, 1.5 + pointCount / 3);
}

// Extract a 4-digit year from an ISO-ish datetime string. Returns null if absent.
export function parseYear(dt) {
  if (!dt) return null;
  const m = /(-?\d{4})/.exec(String(dt));
  return m ? parseInt(m[1], 10) : null;
}

export const ZONE_COLORS = {
  A: [255, 100, 80],
  B: [80, 160, 255],
  C: [100, 220, 160],
  D: [255, 180, 80],
  E: [200, 100, 255],
};

export function getZoneColor(zoneId) {
  return ZONE_COLORS[zoneId] || [150, 150, 150];
}

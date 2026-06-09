"""
Convergence Score (C-Score) Analysis.

For every 0.5° geographic grid cell over the continental US and Zone E
(Western Pacific), compute how many independent data layers have events
nearby, weighted by tier confidence, population density, and military
airspace masking.

Formula:
    C-Score = Σ(active layers with event within radius R and time window T)
              × confidence_weight(tier)
              × population_correction_factor
              × (1 - military_masking_penalty if inside SUA)

Confidence weights: Tier 1 = 1.0, Tier 2 = 0.6, Tier 3 = 0.3

Output:
  output/analysis/convergence_scores.geojson   — full grid GeoJSON
  output/analysis/top_zones.json               — top 25 zones with breakdown
  output/analysis/convergence_summary.json     — aggregate stats
"""

import json
import math
import sys
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import OUTPUT_DIR, get_logger, load_registry, load_geojson

log = get_logger("convergence_score")

LAYERS_DIR = OUTPUT_DIR / "layers"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"

# ── Analysis parameters ──────────────────────────────────────────────────────
RADIUS_KM = 50.0          # Default search radius around each grid cell centroid
GRID_RESOLUTION = 0.5     # Degrees (≈55 km)
EARTH_RADIUS_KM = 6371.0
TOP_N = 25                # How many zones to emit in top_zones.json

# Continental US bounding box
CONUS_LAT_MIN, CONUS_LAT_MAX = 24.0, 50.0
CONUS_LON_MIN, CONUS_LON_MAX = -125.0, -66.0

# Zone E (Western Pacific / Japan Trench) bounding box — from registry
ZONE_E_LAT_MIN, ZONE_E_LAT_MAX = 30.0, 45.0
ZONE_E_LON_MIN, ZONE_E_LON_MAX = 130.0, 150.0

# Tier → confidence weight
TIER_WEIGHTS = {1: 1.0, 2: 0.6, 3: 0.3}

# Military masking penalty (inside SUA → × 0.6, i.e. penalty = 0.4)
MILITARY_PENALTY = 0.4

# Hard C-Score ceiling
CSCORE_MAX = 10.0

# Geology notes for known regions (keyed by approximate zone label)
GEOLOGY_NOTES = {
    "A": "Rio Grande Rift proximity",
    "B": "Southern California offshore — active submarine faults",
    "C": "Hessdalen Valley analog — solved geophysical light phenomenon",
    "D": "New Madrid Seismic Zone — intraplate fault system",
    "E": "Japan Trench — densest post-Tohoku ocean sensor network",
}


# ── Geometry helpers ─────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two (lat, lon) points."""
    r = EARTH_RADIUS_KM
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(max(0.0, min(1.0, a))))


def point_in_polygon(px: float, py: float, polygon: list) -> bool:
    """
    Ray-casting polygon test.
    polygon is a list of [lon, lat] coordinate pairs (GeoJSON ring convention).
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_geojson_polygon(lon: float, lat: float, feature: dict) -> bool:
    """
    Check whether (lon, lat) is inside a GeoJSON Feature with Polygon or
    MultiPolygon geometry.  Uses shapely.geometry when available, falls back
    to the ray-casting implementation above.
    """
    try:
        from shapely.geometry import Point, shape  # type: ignore
        geom = shape(feature.get("geometry", {}))
        return geom.contains(Point(lon, lat))
    except ImportError:
        pass

    geom = feature.get("geometry", {})
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])

    if gtype == "Polygon":
        outer = coords[0] if coords else []
        if not point_in_polygon(lon, lat, outer):
            return False
        for hole in coords[1:]:
            if point_in_polygon(lon, lat, hole):
                return False
        return True

    if gtype == "MultiPolygon":
        for poly_coords in coords:
            outer = poly_coords[0] if poly_coords else []
            if point_in_polygon(lon, lat, outer):
                inside_hole = any(
                    point_in_polygon(lon, lat, hole)
                    for hole in poly_coords[1:]
                )
                if not inside_hole:
                    return True
        return False

    return False


# ── Grid generation ──────────────────────────────────────────────────────────

def generate_grid_cells() -> list[tuple[float, float]]:
    """
    Return (lat, lon) centroid pairs for every 0.5° cell over CONUS + Zone E.
    """
    cells = []
    step = GRID_RESOLUTION

    # CONUS
    lat = CONUS_LAT_MIN
    while lat <= CONUS_LAT_MAX:
        lon = CONUS_LON_MIN
        while lon <= CONUS_LON_MAX:
            cells.append((round(lat, 4), round(lon, 4)))
            lon = round(lon + step, 4)
        lat = round(lat + step, 4)

    # Zone E (Western Pacific)
    lat = ZONE_E_LAT_MIN
    while lat <= ZONE_E_LAT_MAX:
        lon = ZONE_E_LON_MIN
        while lon <= ZONE_E_LON_MAX:
            cells.append((round(lat, 4), round(lon, 4)))
            lon = round(lon + step, 4)
        lat = round(lat + step, 4)

    return cells


# ── Data loaders ─────────────────────────────────────────────────────────────

def load_layer_events(layers_dir: Path) -> dict[str, list[tuple[float, float]]]:
    """
    Load all normalised layer GeoJSON files.
    Returns dict: layer_name → list of (lat, lon) tuples.
    """
    events: dict[str, list[tuple[float, float]]] = {}
    geojson_files = sorted(layers_dir.glob("*.geojson"))
    if not geojson_files:
        log.warning(f"No GeoJSON files found in {layers_dir}")
    for path in geojson_files:
        layer_name = path.stem
        try:
            gj = load_geojson(path)
            pts = []
            for feat in gj.get("features", []):
                coords = feat.get("geometry", {}).get("coordinates", [])
                if len(coords) >= 2:
                    pts.append((float(coords[1]), float(coords[0])))  # (lat, lon)
            events[layer_name] = pts
            log.info(f"  Loaded layer '{layer_name}': {len(pts)} events")
        except Exception as exc:
            log.warning(f"  Could not load {path.name}: {exc}")
    return events


def load_sua_polygons(layers_dir: Path) -> list[dict]:
    """Load FAA special use airspace polygons if available."""
    sua_path = layers_dir / "faa_airspace_polygons.geojson"
    if not sua_path.exists():
        # Fallback: look in output/layers/faa_airspace.geojson
        sua_path = layers_dir / "faa_airspace.geojson"
    if not sua_path.exists():
        log.info("FAA airspace polygon file not found — military masking disabled")
        return []
    try:
        gj = load_geojson(sua_path)
        features = gj.get("features", [])
        log.info(f"Loaded {len(features)} SUA polygon features")
        return features
    except Exception as exc:
        log.warning(f"Could not load SUA polygons: {exc}")
        return []


def load_population_corrections(analysis_dir: Path) -> dict[str, dict]:
    """
    Load all population_corrected_<layer>.json files.
    Returns dict: layer_name → {(lat_bin, lon_bin): cell_data}
    """
    corrections: dict[str, dict] = {}
    for path in sorted(analysis_dir.glob("population_corrected_*.json")):
        layer_name = path.stem.replace("population_corrected_", "")
        try:
            with open(path) as f:
                data = json.load(f)
            cell_map = {}
            for cell in data.get("grid_cells", []):
                key = (round(cell["lat"] / GRID_RESOLUTION) * GRID_RESOLUTION,
                       round(cell["lon"] / GRID_RESOLUTION) * GRID_RESOLUTION)
                cell_map[key] = cell
            corrections[layer_name] = cell_map
            log.info(f"  Loaded population correction for '{layer_name}': {len(cell_map)} cells")
        except Exception as exc:
            log.warning(f"  Could not load {path.name}: {exc}")
    return corrections


# ── C-Score computation ──────────────────────────────────────────────────────

def is_inside_sua(lat: float, lon: float, sua_features: list[dict]) -> bool:
    """Return True if (lat, lon) falls inside any SUA polygon."""
    for feat in sua_features:
        if point_in_geojson_polygon(lon, lat, feat):
            return True
    return False


def events_in_radius(
    cell_lat: float,
    cell_lon: float,
    points: list[tuple[float, float]],
    radius_km: float,
) -> int:
    """Count how many (lat, lon) points fall within radius_km of the cell centroid."""
    if not points:
        return 0
    count = 0
    for lat, lon in points:
        if haversine_km(cell_lat, cell_lon, lat, lon) <= radius_km:
            count += 1
    return count


def population_correction_factor(
    cell_lat: float,
    cell_lon: float,
    layer_name: str,
    pop_corrections: dict[str, dict],
    registry: dict,
) -> tuple[float, dict]:
    """
    Compute population correction multiplier.

    For population-biased layers (observation-dependent), we use the z-score
    from population_control output to modulate the contribution:
      - z > 2  (cluster exceeds expected density) → boost factor > 1
      - z <= 0 (cluster at or below expected)     → factor = 0.5 (penalise)
      - no data                                   → factor = 1.0 (neutral)

    Returns: (factor, info_dict)
    """
    registry_layers = registry.get("layers", {})
    pop_biased = set(registry.get("analysis_filters", {}).get("population_biased_layers", []))

    if layer_name not in pop_biased:
        return 1.0, {"expected": None, "observed": None, "z_score": None}

    layer_corrections = pop_corrections.get(layer_name, {})
    lat_bin = round(cell_lat / GRID_RESOLUTION) * GRID_RESOLUTION
    lon_bin = round(cell_lon / GRID_RESOLUTION) * GRID_RESOLUTION
    cell = layer_corrections.get((lat_bin, lon_bin))

    if cell is None:
        return 1.0, {"expected": None, "observed": None, "z_score": None}

    z = cell.get("z_score", 0.0)
    expected = cell.get("expected_count")
    observed = cell.get("observed_count")

    # Sigmoid-like mapping: z → correction factor clamped to [0.5, 2.0]
    factor = max(0.5, min(2.0, 1.0 + 0.25 * z))
    return round(factor, 4), {
        "expected": expected,
        "observed": observed,
        "z_score": round(z, 3),
    }


def nearest_zone(cell_lat: float, cell_lon: float, zones: dict) -> Optional[str]:
    """Return the zone ID whose bbox contains the cell, or None."""
    for zone_id, zone_meta in zones.items():
        bbox = zone_meta.get("bbox", {})
        if (bbox.get("min_lat", -999) <= cell_lat <= bbox.get("max_lat", 999) and
                bbox.get("min_lon", -999) <= cell_lon <= bbox.get("max_lon", 999)):
            return zone_id
    return None


def compute_cscore(
    cell_lat: float,
    cell_lon: float,
    layer_events: dict[str, list[tuple[float, float]]],
    registry: dict,
    sua_features: list[dict],
    pop_corrections: dict[str, dict],
    radius_km: float = RADIUS_KM,
) -> tuple[float, list[dict], dict, dict]:
    """
    Compute the C-Score for a single grid cell.

    Returns:
        (c_score, layers_present, pop_info, military_info)
    """
    registry_layers = registry.get("layers", {})
    zones = registry.get("zones_of_interest", {})

    weighted_sum = 0.0
    layers_present = []
    pop_info = {"expected": None, "observed": None, "z_score": None}
    best_pop_z = None

    for layer_name, pts in layer_events.items():
        meta = registry_layers.get(layer_name, {})
        tier = meta.get("tier", 3)
        weight = TIER_WEIGHTS.get(tier, 0.3)

        count = events_in_radius(cell_lat, cell_lon, pts, radius_km)
        if count == 0:
            continue

        # Per-layer population correction
        pop_factor, pcell = population_correction_factor(
            cell_lat, cell_lon, layer_name, pop_corrections, registry
        )

        contribution = weight * pop_factor
        weighted_sum += contribution

        layers_present.append({
            "layer": layer_name,
            "events_in_radius": count,
            "tier": tier,
            "weight": weight,
            "pop_factor": pop_factor,
            "contribution": round(contribution, 4),
        })

        # Track the most informative population correction result
        if pcell.get("z_score") is not None:
            if best_pop_z is None or abs(pcell["z_score"]) > abs(best_pop_z):
                pop_info = pcell
                best_pop_z = pcell["z_score"]

    if not layers_present:
        return 0.0, [], pop_info, {"inside_sua": False, "penalty_applied": 0.0}

    # ── Military masking ──────────────────────────────────────────────────────
    inside_sua = is_inside_sua(cell_lat, cell_lon, sua_features) if sua_features else False
    military_penalty = MILITARY_PENALTY if inside_sua else 0.0
    military_info = {
        "inside_sua": inside_sua,
        "penalty_applied": round(military_penalty, 4),
    }

    # ── Final score (scale to 0-10) ───────────────────────────────────────────
    # Maximum theoretic weighted sum = number of layers × max_weight (1.0) × max_pop_factor (2.0)
    max_possible = len(layer_events) * TIER_WEIGHTS[1] * 2.0
    if max_possible <= 0:
        return 0.0, layers_present, pop_info, military_info

    raw_score = weighted_sum * (1.0 - military_penalty)
    c_score = min(CSCORE_MAX, (raw_score / max_possible) * CSCORE_MAX * 2.5)
    c_score = round(c_score, 4)

    return c_score, layers_present, pop_info, military_info


# ── Public API ────────────────────────────────────────────────────────────────

def get_cscore_for_point(
    lat: float,
    lon: float,
    radius_km: float = RADIUS_KM,
    layers_dir: Optional[Path] = None,
) -> float:
    """
    Compute the C-Score for an arbitrary (lat, lon) point.

    This is the Phase 2 frontend entry point for "What else is here?" queries.

    Args:
        lat:        Latitude of query point.
        lon:        Longitude of query point.
        radius_km:  Search radius in km (default RADIUS_KM = 50).
        layers_dir: Path to normalised layer GeoJSON directory.
                    Defaults to output/layers/.

    Returns:
        C-Score in [0, 10].
    """
    if layers_dir is None:
        layers_dir = LAYERS_DIR

    registry = load_registry()
    layer_events = load_layer_events(layers_dir)
    sua_features = load_sua_polygons(layers_dir)
    pop_corrections = load_population_corrections(ANALYSIS_DIR)

    c_score, _, _, _ = compute_cscore(
        lat, lon,
        layer_events=layer_events,
        registry=registry,
        sua_features=sua_features,
        pop_corrections=pop_corrections,
        radius_km=radius_km,
    )
    return c_score


# ── Main analysis pipeline ────────────────────────────────────────────────────

def main():
    log.info("=== convergence_score.py ===")
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load inputs ───────────────────────────────────────────────────────────
    log.info("\nLoading layer events…")
    layer_events = load_layer_events(LAYERS_DIR)
    if not layer_events:
        log.warning("No layer data found in output/layers/ — scores will be zero everywhere.")

    log.info("\nLoading FAA SUA polygons…")
    sua_features = load_sua_polygons(LAYERS_DIR)

    log.info("\nLoading population correction data…")
    pop_corrections = load_population_corrections(ANALYSIS_DIR)

    registry = load_registry()
    registry_layers = registry.get("layers", {})
    zones = registry.get("zones_of_interest", {})

    # ── Generate grid ─────────────────────────────────────────────────────────
    log.info("\nGenerating grid cells (CONUS + Zone E)…")
    grid_cells = generate_grid_cells()
    log.info(f"  {len(grid_cells)} grid cells to evaluate")

    # ── Compute C-Scores ──────────────────────────────────────────────────────
    log.info("\nComputing C-Scores…")
    results = []

    for idx, (cell_lat, cell_lon) in enumerate(grid_cells):
        if idx > 0 and idx % 500 == 0:
            log.info(f"  {idx}/{len(grid_cells)} cells processed…")

        c_score, layers_present, pop_info, military_info = compute_cscore(
            cell_lat, cell_lon,
            layer_events=layer_events,
            registry=registry,
            sua_features=sua_features,
            pop_corrections=pop_corrections,
            radius_km=RADIUS_KM,
        )

        if c_score == 0.0 and not layers_present:
            continue  # Skip empty cells to keep output manageable

        zone_id = nearest_zone(cell_lat, cell_lon, zones)
        geo_note = GEOLOGY_NOTES.get(zone_id, "") if zone_id else ""

        results.append({
            "lat": cell_lat,
            "lon": cell_lon,
            "c_score": c_score,
            "layer_count": len(layers_present),
            "layers_present": layers_present,
            "population_correction": pop_info,
            "military_masking": military_info,
            "geology_notes": geo_note,
            "nearest_zone": zone_id,
        })

    log.info(f"  Done. {len(results)} non-empty cells.")

    # ── Sort and select top zones ─────────────────────────────────────────────
    results.sort(key=lambda x: x["c_score"], reverse=True)

    # ── Build GeoJSON output ──────────────────────────────────────────────────
    log.info("\nWriting convergence_scores.geojson…")
    features = []
    for r in results:
        props = {k: v for k, v in r.items() if k not in ("lat", "lon")}
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [r["lon"], r["lat"]],
            },
            "properties": props,
        })

    from datetime import datetime, timezone
    geojson_out = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "record_count": len(features),
            "radius_km": RADIUS_KM,
            "grid_resolution_deg": GRID_RESOLUTION,
            "layers_evaluated": list(layer_events.keys()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    geojson_path = ANALYSIS_DIR / "convergence_scores.geojson"
    with open(geojson_path, "w") as f:
        json.dump(geojson_out, f, indent=2, default=str)
    log.info(f"  → {geojson_path}")

    # ── Top N zones JSON ──────────────────────────────────────────────────────
    log.info(f"\nWriting top {TOP_N} zones…")
    top_zones = []
    for rank_idx, r in enumerate(results[:TOP_N], start=1):
        top_zones.append({
            "rank": rank_idx,
            "lat": r["lat"],
            "lon": r["lon"],
            "c_score": r["c_score"],
            "layer_count": r["layer_count"],
            "layers_present": r["layers_present"],
            "population_correction": r["population_correction"],
            "military_masking": r["military_masking"],
            "geology_notes": r["geology_notes"],
            "nearest_zone": r["nearest_zone"],
        })

    top_zones_path = ANALYSIS_DIR / "top_zones.json"
    with open(top_zones_path, "w") as f:
        json.dump(top_zones, f, indent=2)
    log.info(f"  → {top_zones_path}")

    if top_zones:
        log.info("\n  Top 5 convergence zones:")
        for z in top_zones[:5]:
            log.info(
                f"    #{z['rank']} lat={z['lat']}, lon={z['lon']} | "
                f"C-Score={z['c_score']:.2f} | layers={z['layer_count']} | "
                f"zone={z['nearest_zone']}"
            )

    # ── Summary stats ─────────────────────────────────────────────────────────
    all_scores = [r["c_score"] for r in results]
    all_layer_counts = [r["layer_count"] for r in results]

    summary = {
        "total_cells_evaluated": len(grid_cells),
        "non_empty_cells": len(results),
        "radius_km": RADIUS_KM,
        "grid_resolution_deg": GRID_RESOLUTION,
        "layers_evaluated": list(layer_events.keys()),
        "layer_count": len(layer_events),
        "score_stats": {
            "max": round(float(np.max(all_scores)), 4) if all_scores else 0.0,
            "mean": round(float(np.mean(all_scores)), 4) if all_scores else 0.0,
            "median": round(float(np.median(all_scores)), 4) if all_scores else 0.0,
            "std": round(float(np.std(all_scores)), 4) if all_scores else 0.0,
            "p90": round(float(np.percentile(all_scores, 90)), 4) if all_scores else 0.0,
            "p95": round(float(np.percentile(all_scores, 95)), 4) if all_scores else 0.0,
            "p99": round(float(np.percentile(all_scores, 99)), 4) if all_scores else 0.0,
        },
        "layer_convergence_stats": {
            "max_layers_in_one_cell": int(np.max(all_layer_counts)) if all_layer_counts else 0,
            "mean_layers_per_cell": round(float(np.mean(all_layer_counts)), 3) if all_layer_counts else 0.0,
            "cells_with_5plus_layers": int(sum(1 for c in all_layer_counts if c >= 5)),
            "cells_with_3plus_layers": int(sum(1 for c in all_layer_counts if c >= 3)),
        },
        "military_masking": {
            "cells_inside_sua": int(sum(1 for r in results if r["military_masking"]["inside_sua"])),
        },
        "top_zone": top_zones[0] if top_zones else None,
    }

    summary_path = ANALYSIS_DIR / "convergence_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log.info(f"\nSummary → {summary_path}")

    log.info("\n=== Convergence score analysis complete ===")
    if top_zones:
        best = top_zones[0]
        log.info(
            f"STRONGEST SIGNAL: lat={best['lat']}, lon={best['lon']} | "
            f"C-Score={best['c_score']:.2f} | {best['layer_count']} layers | "
            f"Zone {best['nearest_zone']}"
        )


if __name__ == "__main__":
    main()

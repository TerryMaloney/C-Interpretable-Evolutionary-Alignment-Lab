"""
Spatial clustering analysis using DBSCAN.

Runs on:
  1. Each layer individually
  2. Cross-layer (all Tier 1 layers combined)
  3. Per-zone analysis (Zones A, B, C, D)

Algorithm: DBSCAN (Density-Based Spatial Clustering of Applications with Noise)
  - Does not require predefined cluster count
  - Handles irregular cluster shapes
  - Labels outliers as noise (-1)

Distance metric: Haversine (great-circle distance in km)

Output:
  output/analysis/clusters_<layer>.json       per-layer results
  output/analysis/clusters_crosslayer.json    multi-layer convergence
  output/analysis/cluster_summary.json        all findings ranked by significance
"""

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.cluster import DBSCAN

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import OUTPUT_DIR, get_logger, load_geojson, load_registry

log = get_logger("clustering")

LAYERS_DIR = OUTPUT_DIR / "layers"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"

# DBSCAN parameters
EPS_KM = 50        # Cluster radius in km
MIN_SAMPLES = 5    # Minimum points to form a cluster
EARTH_RADIUS_KM = 6371.0

# Layers to include in cross-layer analysis (Tier 1 only for Phase 1)
TIER1_LAYERS = ["nuforc", "noaa_ume", "usgs_seismic", "nuclear_facilities", "epa_radnet"]

# Zone bounding boxes from registry
ZONES = None  # Loaded from registry at runtime


def haversine_matrix(coords: np.ndarray) -> np.ndarray:
    """
    Compute pairwise haversine distance matrix.
    coords: (N, 2) array of [lat, lon] in degrees
    Returns: (N, N) distance matrix in km
    """
    lat = np.radians(coords[:, 0])
    lon = np.radians(coords[:, 1])
    n = len(lat)

    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]

    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    return EARTH_RADIUS_KM * c


def run_dbscan(coords: np.ndarray, eps_km: float = EPS_KM, min_samples: int = MIN_SAMPLES) -> np.ndarray:
    """Run DBSCAN with haversine metric. Returns label array."""
    if len(coords) < min_samples:
        return np.full(len(coords), -1)

    # sklearn DBSCAN with precomputed distances for haversine
    dist_matrix = haversine_matrix(coords)
    db = DBSCAN(eps=eps_km, min_samples=min_samples, metric="precomputed")
    return db.fit_predict(dist_matrix)


def extract_coords(layer_path: Path, bbox: dict | None = None) -> tuple[np.ndarray, list[dict]]:
    """Load layer GeoJSON and return coordinate array + feature list, optionally filtered to bbox."""
    gj = load_geojson(layer_path)
    features = gj.get("features", [])

    coords = []
    valid_features = []

    for feat in features:
        geom = feat.get("geometry", {})
        c = geom.get("coordinates", [])
        if len(c) < 2:
            continue
        lon, lat = c[0], c[1]

        if bbox:
            if not (bbox["min_lat"] <= lat <= bbox["max_lat"] and
                    bbox["min_lon"] <= lon <= bbox["max_lon"]):
                continue

        coords.append([lat, lon])
        valid_features.append(feat)

    return np.array(coords) if coords else np.empty((0, 2)), valid_features


def summarize_clusters(labels: np.ndarray, features: list[dict], layer: str) -> dict:
    """Build cluster summary statistics."""
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int(np.sum(labels == -1))

    clusters = []
    for cluster_id in range(n_clusters):
        mask = labels == cluster_id
        cluster_features = [f for f, m in zip(features, mask) if m]
        cluster_coords = np.array([
            [f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]]
            for f in cluster_features
        ])

        center_lat = float(np.mean(cluster_coords[:, 0]))
        center_lon = float(np.mean(cluster_coords[:, 1]))
        radius_km = float(np.max(haversine_matrix(cluster_coords))) if len(cluster_coords) > 1 else 0

        clusters.append({
            "cluster_id": cluster_id,
            "size": int(np.sum(mask)),
            "center_lat": round(center_lat, 4),
            "center_lon": round(center_lon, 4),
            "radius_km": round(radius_km, 1),
            "layers_present": [layer],
        })

    clusters.sort(key=lambda x: x["size"], reverse=True)

    return {
        "layer": layer,
        "total_records": len(features),
        "n_clusters": n_clusters,
        "n_noise": n_noise,
        "cluster_rate": round((len(features) - n_noise) / max(len(features), 1), 3),
        "clusters": clusters,
    }


def run_layer_clustering():
    """Run DBSCAN on each available layer."""
    all_results = {}
    layer_files = sorted(LAYERS_DIR.glob("*.geojson"))

    for path in layer_files:
        layer = path.stem
        log.info(f"Clustering layer: {layer}")
        coords, features = extract_coords(path)

        if len(coords) < MIN_SAMPLES:
            log.info(f"  Too few records ({len(coords)}) — skipping")
            continue

        labels = run_dbscan(coords)
        result = summarize_clusters(labels, features, layer)
        all_results[layer] = result

        log.info(
            f"  {layer}: {result['n_clusters']} clusters, "
            f"{result['n_noise']} noise, "
            f"cluster_rate={result['cluster_rate']:.1%}"
        )

        out_path = ANALYSIS_DIR / f"clusters_{layer}.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)

    return all_results


def run_crosslayer_clustering():
    """
    Find geographic zones where multiple layers co-cluster.
    For each grid cell, count how many Tier1 layers have a cluster centroid within EPS_KM.
    """
    log.info("\nRunning cross-layer convergence analysis…")

    layer_cluster_centers = {}
    for layer in TIER1_LAYERS:
        path = LAYERS_DIR / f"{layer}.geojson"
        if not path.exists():
            continue
        result_path = ANALYSIS_DIR / f"clusters_{layer}.json"
        if not result_path.exists():
            continue
        with open(result_path) as f:
            data = json.load(f)
        centers = [(c["center_lat"], c["center_lon"], c["size"]) for c in data.get("clusters", [])]
        layer_cluster_centers[layer] = centers
        log.info(f"  {layer}: {len(centers)} cluster centers")

    if not layer_cluster_centers:
        log.warning("No cluster centers available — run layer clustering first")
        return []

    # Find zones where >= 2 layers have clusters within EPS_KM
    convergence_zones = []
    all_centers = [(lat, lon, size, layer)
                   for layer, centers in layer_cluster_centers.items()
                   for lat, lon, size in centers]

    visited = set()
    for i, (lat1, lon1, size1, layer1) in enumerate(all_centers):
        if i in visited:
            continue

        nearby_layers = {layer1: (lat1, lon1, size1)}
        for j, (lat2, lon2, size2, layer2) in enumerate(all_centers):
            if i == j or layer2 == layer1:
                continue
            dist = haversine_matrix(np.array([[lat1, lon1], [lat2, lon2]]))[0, 1]
            if dist <= EPS_KM * 2:  # 2x eps for cross-layer
                if layer2 not in nearby_layers or size2 > nearby_layers[layer2][2]:
                    nearby_layers[layer2] = (lat2, lon2, size2)

        if len(nearby_layers) >= 2:
            visited.add(i)
            lats = [v[0] for v in nearby_layers.values()]
            lons = [v[1] for v in nearby_layers.values()]
            convergence_zones.append({
                "center_lat": round(float(np.mean(lats)), 4),
                "center_lon": round(float(np.mean(lons)), 4),
                "layers_converging": list(nearby_layers.keys()),
                "layer_count": len(nearby_layers),
                "total_records": sum(v[2] for v in nearby_layers.values()),
            })

    convergence_zones.sort(key=lambda x: x["layer_count"], reverse=True)

    log.info(f"\nCross-layer convergence zones found: {len(convergence_zones)}")
    for zone in convergence_zones[:10]:
        log.info(
            f"  lat={zone['center_lat']}, lon={zone['center_lon']} | "
            f"{zone['layer_count']} layers: {', '.join(zone['layers_converging'])}"
        )

    out_path = ANALYSIS_DIR / "clusters_crosslayer.json"
    with open(out_path, "w") as f:
        json.dump({"convergence_zones": convergence_zones}, f, indent=2)

    return convergence_zones


def run_zone_analysis(zones: dict):
    """Run clustering within each named zone of interest."""
    log.info("\nRunning zone-specific analysis…")
    zone_results = {}

    for zone_id, zone_meta in zones.items():
        bbox = zone_meta.get("bbox")
        if not bbox:
            continue
        log.info(f"\nZone {zone_id}: {zone_meta['name']}")

        zone_layer_results = {}
        for path in sorted(LAYERS_DIR.glob("*.geojson")):
            layer = path.stem
            coords, features = extract_coords(path, bbox=bbox)
            if len(coords) < 3:
                continue
            labels = run_dbscan(coords, eps_km=EPS_KM / 2, min_samples=3)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            log.info(f"  {layer}: {len(coords)} records, {n_clusters} clusters")
            zone_layer_results[layer] = {"records": len(coords), "clusters": n_clusters}

        zone_results[zone_id] = {
            "zone_name": zone_meta["name"],
            "bbox": bbox,
            "layers": zone_layer_results,
        }

    out_path = ANALYSIS_DIR / "clusters_by_zone.json"
    with open(out_path, "w") as f:
        json.dump(zone_results, f, indent=2)

    return zone_results


def main():
    log.info("=== clustering.py ===")
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    registry = load_registry()
    zones = registry.get("zones_of_interest", {})

    # Per-layer clustering
    layer_results = run_layer_clustering()

    # Cross-layer convergence
    convergence = run_crosslayer_clustering()

    # Zone-specific analysis
    zone_results = run_zone_analysis(zones)

    # Master summary
    summary = {
        "per_layer": {
            k: {
                "n_clusters": v["n_clusters"],
                "cluster_rate": v["cluster_rate"],
                "top_cluster_size": v["clusters"][0]["size"] if v["clusters"] else 0,
            }
            for k, v in layer_results.items()
        },
        "crosslayer_convergence_zones": len(convergence),
        "top_convergence": convergence[:5],
        "zone_summaries": {
            zid: {zl: zdata["layers"].get(zl, {}) for zl in TIER1_LAYERS}
            for zid, zdata in zone_results.items()
        },
    }

    summary_path = ANALYSIS_DIR / "cluster_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    log.info(f"\nClustering complete. Summary → {summary_path}")
    if convergence:
        log.info(f"\nSTRONGEST SIGNAL — Top convergence zone:")
        top = convergence[0]
        log.info(f"  {top['layer_count']} layers at lat={top['center_lat']}, lon={top['center_lon']}")
        log.info(f"  Layers: {', '.join(top['layers_converging'])}")


if __name__ == "__main__":
    main()

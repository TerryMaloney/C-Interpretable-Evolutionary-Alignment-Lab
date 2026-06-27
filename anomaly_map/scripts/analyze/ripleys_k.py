"""
Ripley's K / L-function — global clustering-vs-randomness test.

Complements DBSCAN (clustering.py): instead of carving out clusters, it answers a single
statistical question per layer/zone — "is this point set more clustered than complete spatial
randomness (CSR), and at what spatial scale?" — with a Monte Carlo confidence envelope.

For each radius r:
  K(r) = A / (N(N-1)) * #{ordered pairs i!=j : dist <= r}
  L(r) = sqrt(K(r) / pi)        # under CSR, E[L(r)] = r
We report L(r) - r. Above the upper CSR envelope => clustered at scale r; below => dispersed.
This feeds the R-Score narrative ("clustered beyond chance at r <= X km").

Output: output/analysis/ripleys_k.json   (per-layer + per-zone curves + verdicts)

Self-test (numpy/scipy only):
  python scripts/analyze/ripleys_k.py --selftest
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np

EARTH_RADIUS_KM = 6371.0
RADII_KM = np.array([10, 25, 50, 75, 100, 150, 200, 300], dtype=float)
ENVELOPE_SIMS = 99           # CSR Monte Carlo realizations (99 -> ~0.01 envelope resolution)
MIN_POINTS = 8
LAYERS = ["bluebook_unknowns", "geipan_cat_d", "cefaa_cases", "nuforc",
          "usgs_seismic", "noaa_ume", "bfro_sightings"]


def project_azeq(coords: np.ndarray, lat0: float, lon0: float) -> np.ndarray:
    lat = np.radians(coords[:, 0]); lon = np.radians(coords[:, 1])
    lat0r, lon0r = math.radians(lat0), math.radians(lon0)
    cos_c = np.clip(np.sin(lat0r) * np.sin(lat)
                    + np.cos(lat0r) * np.cos(lat) * np.cos(lon - lon0r), -1, 1)
    c = np.arccos(cos_c)
    with np.errstate(divide="ignore", invalid="ignore"):
        kp = np.where(c < 1e-12, 1.0, c / np.sin(c))
    x = kp * np.cos(lat) * np.sin(lon - lon0r)
    y = kp * (np.cos(lat0r) * np.sin(lat) - np.sin(lat0r) * np.cos(lat) * np.cos(lon - lon0r))
    return np.column_stack([x * EARTH_RADIUS_KM, y * EARTH_RADIUS_KM])


def l_function(pts: np.ndarray, radii: np.ndarray, area: float) -> np.ndarray:
    """L(r) for a planar point set using a KD-tree pair count (no edge correction)."""
    from scipy.spatial import cKDTree
    n = len(pts)
    if n < 2:
        return np.zeros_like(radii)
    tree = cKDTree(pts)
    counts = tree.count_neighbors(tree, radii)        # ordered pairs incl. self
    pairs = counts - n                                # exclude self-pairs
    k = area / (n * (n - 1)) * pairs
    return np.sqrt(np.maximum(k, 0) / math.pi)


def csr_envelope(n: int, lo: np.ndarray, hi: np.ndarray, radii: np.ndarray,
                 area: float, sims: int, rng: np.random.Generator):
    """Monte Carlo CSR envelope: L(r) percentiles over `sims` uniform fields."""
    curves = np.empty((sims, len(radii)))
    for s in range(sims):
        rp = rng.uniform(lo, hi, size=(n, 2))
        curves[s] = l_function(rp, radii, area)
    return (np.percentile(curves, 2.5, axis=0),
            np.percentile(curves, 50, axis=0),
            np.percentile(curves, 97.5, axis=0))


def analyze_points(coords: np.ndarray, sims: int = ENVELOPE_SIMS, seed: int = 11) -> dict:
    """Run the L-function + CSR envelope for one lat/lon point set."""
    n = len(coords)
    if n < MIN_POINTS:
        return {"n": n, "note": "too few points"}
    lat0, lon0 = float(coords[:, 0].mean()), float(coords[:, 1].mean())
    pts = project_azeq(coords, lat0, lon0)
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    area = float((hi[0] - lo[0]) * (hi[1] - lo[1]))
    if area <= 0:
        return {"n": n, "note": "degenerate extent"}
    radii = RADII_KM[RADII_KM < max(hi - lo)]          # don't probe beyond the extent
    if len(radii) < 2:
        return {"n": n, "note": "extent too small for chosen radii"}
    rng = np.random.default_rng(seed)
    l_obs = l_function(pts, radii, area)
    lo_env, med_env, hi_env = csr_envelope(n, lo, hi, radii, area, sims, rng)
    clustered = [float(r) for r, o, h in zip(radii, l_obs, hi_env) if o > h]
    verdict = (f"clustered beyond CSR at r <= {max(clustered):.0f} km"
               if clustered else "indistinguishable from spatial randomness")
    return {
        "n": n, "radii_km": radii.tolist(),
        "L_observed": [round(v, 1) for v in l_obs.tolist()],
        "L_csr_lo": [round(v, 1) for v in lo_env.tolist()],
        "L_csr_hi": [round(v, 1) for v in hi_env.tolist()],
        "clustered_radii_km": clustered, "verdict": verdict,
    }


def selftest() -> int:
    print("=== ripleys_k.py self-test ===")
    rng = np.random.default_rng(3)
    ok = True
    # Clustered: 5 tight blobs (in lat/lon degrees, ~continental spread).
    centers = rng.uniform([30, -120], [48, -70], size=(5, 2))
    clus = np.vstack([c + rng.normal(0, 0.2, size=(30, 2)) for c in centers])
    res_c = analyze_points(clus, sims=60)
    print(f"  clustered set (n={res_c['n']}): {res_c['verdict']}")
    if not res_c.get("clustered_radii_km"):
        print("  FAIL: clustered set not detected as clustered"); ok = False
    # Uniform: should fall within the CSR envelope (no clustering verdict).
    uni = rng.uniform([30, -120], [48, -70], size=(150, 2))
    res_u = analyze_points(uni, sims=60)
    print(f"  uniform set   (n={res_u['n']}): {res_u['verdict']}")
    if res_u.get("clustered_radii_km"):
        print(f"  WARN: uniform set flagged clustered at {res_u['clustered_radii_km']} "
              "(occasional false positive is statistically expected)")
    print("=== PASS ===" if ok else "=== FAIL ===")
    return 0 if ok else 1


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.common import OUTPUT_DIR, get_logger, load_geojson, save_geojson, load_registry
    log = get_logger("ripleys_k")
    log.info("=== ripleys_k.py ===")
    layers_dir = OUTPUT_DIR / "layers"
    analysis_dir = OUTPUT_DIR / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    def coords_for(path, bbox=None):
        out = []
        for f in load_geojson(path).get("features", []):
            c = f.get("geometry", {}).get("coordinates", [])
            if len(c) >= 2:
                lat, lon = c[1], c[0]
                if bbox and not (bbox["min_lat"] <= lat <= bbox["max_lat"]
                                 and bbox["min_lon"] <= lon <= bbox["max_lon"]):
                    continue
                out.append([lat, lon])
        return np.array(out) if out else np.empty((0, 2))

    results = {"by_layer": {}, "by_zone": {}}
    for name in LAYERS:
        path = layers_dir / f"{name}.geojson"
        if not path.exists():
            continue
        coords = coords_for(path)
        log.info(f"  {name}: {len(coords)} points")
        results["by_layer"][name] = analyze_points(coords)

    zones = load_registry().get("zones_of_interest", {})
    for zid, zmeta in zones.items():
        bbox = zmeta.get("bbox")
        if not bbox:
            continue
        all_coords = []
        for path in sorted(layers_dir.glob("*.geojson")):
            c = coords_for(path, bbox=bbox)
            if len(c):
                all_coords.append(c)
        if all_coords:
            stacked = np.vstack(all_coords)
            results["by_zone"][zid] = {"zone_name": zmeta.get("name"),
                                       **analyze_points(stacked)}

    if not results["by_layer"] and not results["by_zone"]:
        results["note"] = ("no input layers found — run the fetch + process pipeline "
                           "to populate output/layers/ first")
        log.warning(results["note"])
    save_geojson(results, analysis_dir / "ripleys_k.json")
    log.info(f"Wrote ripleys_k.json → {analysis_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ripley's K / L-function clustering test")
    parser.add_argument("--selftest", action="store_true", help="Run the synthetic self-test")
    args = parser.parse_args()
    if args.selftest:
        sys.exit(selftest())
    main()

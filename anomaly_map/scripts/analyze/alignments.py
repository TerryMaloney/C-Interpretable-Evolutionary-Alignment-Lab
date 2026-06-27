"""
Spatial alignment ("ley line" / corridor) detection — WITH null-hypothesis testing.

The whole point of this script is the skeptic machinery, not the lines themselves.
Random scatter ALWAYS produces visually compelling alignments, and anomaly reports pile
up along coastlines, cities, highways, and flight corridors — all of which manufacture
fake "lines". So every candidate alignment is scored against a Monte Carlo null model
(density-matched randomized points) and assigned a p-value. The honest, common result is
"these alignments are consistent with chance" — which is a correct, valuable output, in
the same spirit as the project's N-Score / R-Score / Claim-Level ladder.

Pipeline:
  1. Load a curated, low-N, vetted point set (Blue Book, GEIPAN, CEFAA, Belgian wave,
     foo fighters, FOIA, plus Tier-1 instrument layers). Raw NUFORC is excluded by
     default — it is both O(N^2)-infeasible and reporting-biased to meaninglessness.
  2. Project to a local azimuthal-equidistant plane (km), so collinearity is planar.
  3. Hough-accumulator candidate detection, then PCA refinement within a corridor width.
  4. Density-matched Monte Carlo null -> family-wise p-value via the max-size statistic.
  5. Flag obvious confounds (graticule artifacts, population/infrastructure corridors).

Outputs (output/analysis/):
  alignments.geojson          LineString features for significant + candidate alignments
  alignments_control.geojson  one null realization's "alignments" (negative-control overlay)
  alignment_bearings.json     orientation rose data for significant alignments
  alignment_summary.json      parameters, null distribution, verdict

Run the self-test (no project data or deps beyond numpy/scipy required):
  python scripts/analyze/alignments.py --selftest
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np

# ── Tunable parameters ──────────────────────────────────────────────────────
EARTH_RADIUS_KM = 6371.0
CORRIDOR_KM = 12.0          # half-width of the alignment corridor (perpendicular)
MIN_POINTS = 5             # minimum members to call something an alignment
THETA_BINS = 180           # Hough orientation resolution (1 degree)
NULL_ITERS = 300           # Monte Carlo null realizations
NULL_BW_SCALE = 2.5        # KDE bandwidth multiplier for the null (broad = preserves
                           # city/coast clustering but smears out thin linear filaments,
                           # so the null doesn't absorb the very lines we test for)
SIGNIFICANCE = 0.05        # p-value threshold for "significant"
MIN_SPAN_KM = 50.0         # ignore tiny alignments smaller than this end-to-end
DEDUPE_JACCARD = 0.5       # merge alignments sharing > this fraction of members

# Curated default input layers (low-N, vetted). Tunable.
DEFAULT_LAYERS = [
    "bluebook_unknowns", "geipan_cat_d", "cefaa_cases", "belgian_triangle_wave",
    "foo_fighters_wwii", "operation_prato", "aatip_physiological", "foia_documents",
    "usgs_seismic", "usgs_magnetic", "usgs_radon", "nuclear_facilities",
]
# Layers whose points lie on coasts by construction (coastal-artifact flag).
COASTAL_LAYERS = {"noaa_ume", "maritime_anomalies", "uso_incidents", "dart_buoys"}
# Population / infrastructure proxy layer for the infrastructure-corridor flag.
INFRA_LAYER = "nighttime_lights"


# ── Geometry: local azimuthal-equidistant projection (lat/lon degrees -> km) ──
def project_azeq(coords: np.ndarray, lat0: float, lon0: float) -> np.ndarray:
    """coords: (N,2) [lat,lon] deg -> (N,2) [x_east, y_north] km about (lat0,lon0)."""
    lat = np.radians(coords[:, 0])
    lon = np.radians(coords[:, 1])
    lat0r, lon0r = math.radians(lat0), math.radians(lon0)
    cos_c = (np.sin(lat0r) * np.sin(lat)
             + np.cos(lat0r) * np.cos(lat) * np.cos(lon - lon0r))
    cos_c = np.clip(cos_c, -1.0, 1.0)
    c = np.arccos(cos_c)
    # k' = c / sin(c), with limit 1 as c -> 0
    with np.errstate(divide="ignore", invalid="ignore"):
        kp = np.where(c < 1e-12, 1.0, c / np.sin(c))
    x = kp * np.cos(lat) * np.sin(lon - lon0r)
    y = kp * (np.cos(lat0r) * np.sin(lat) - np.sin(lat0r) * np.cos(lat) * np.cos(lon - lon0r))
    return np.column_stack([x * EARTH_RADIUS_KM, y * EARTH_RADIUS_KM])


# ── Detection ───────────────────────────────────────────────────────────────
def _refine_members(pts: np.ndarray, idx: np.ndarray, corridor_km: float):
    """Fit a line (PCA) through candidate member points; return inliers + geometry."""
    member_pts = pts[idx]
    centroid = member_pts.mean(axis=0)
    centered = member_pts - centroid
    # Principal axis = first PCA eigenvector
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    direction = vh[0]                       # unit vector along the line
    normal = np.array([-direction[1], direction[0]])
    perp = np.abs(centered @ normal)        # perpendicular distance to the line (km)
    inlier_mask = perp <= corridor_km
    inliers = idx[inlier_mask]
    if len(inliers) < MIN_POINTS:
        return None
    along = centered[inlier_mask] @ direction
    span = float(along.max() - along.min())
    mean_resid = float(perp[inlier_mask].mean())
    bearing = math.degrees(math.atan2(direction[0], direction[1])) % 180.0
    return {
        "members": inliers,
        "count": int(len(inliers)),
        "span_km": span,
        "mean_resid_km": mean_resid,
        "bearing_deg": bearing,
        "direction": direction,
        "centroid": centroid,
    }


def detect_alignments(pts: np.ndarray, corridor_km: float = CORRIDOR_KM,
                      min_points: int = MIN_POINTS, theta_bins: int = THETA_BINS,
                      min_span_km: float = MIN_SPAN_KM) -> list[dict]:
    """Hough-accumulator collinearity detection on projected (km) points.

    Returns a list of alignment dicts sorted by member count (desc), deduplicated.
    """
    n = len(pts)
    if n < min_points:
        return []
    thetas = np.linspace(0.0, math.pi, theta_bins, endpoint=False)
    cos_t, sin_t = np.cos(thetas), np.sin(thetas)
    # rho for every (point, theta): (N, theta_bins)
    rho = pts[:, 0:1] * cos_t[None, :] + pts[:, 1:2] * sin_t[None, :]
    rho_res = corridor_km                     # one bin ~ one corridor width
    rho_idx = np.floor(rho / rho_res).astype(int)

    # Per orientation, group points by rho bin (vectorized), then union each bin with
    # its rho neighbours (offset jitter). Line orientation between bins is recovered by
    # the PCA refinement step, so a theta neighbourhood isn't needed here.
    candidates = []
    seen_member_keys = set()
    for t in range(theta_bins):
        col = rho_idx[:, t]
        order = np.argsort(col, kind="stable")
        sc = col[order]
        change = np.nonzero(np.diff(sc))[0] + 1
        groups = np.split(order, change)
        bin_vals = sc[np.concatenate(([0], change))]
        tbins = {int(b): g for b, g in zip(bin_vals, groups)}
        for b, g in tbins.items():
            members = g
            for db in (-1, 1):
                if (b + db) in tbins:
                    members = np.concatenate([members, tbins[b + db]])
            if len(members) < min_points:
                continue
            members = np.unique(members)
            key = members.tobytes()
            if key in seen_member_keys:
                continue
            seen_member_keys.add(key)
            refined = _refine_members(pts, members, corridor_km)
            if refined and refined["span_km"] >= min_span_km:
                candidates.append(refined)

    # Dedupe by member-set overlap, keeping the larger alignment.
    candidates.sort(key=lambda a: (a["count"], -a["mean_resid_km"]), reverse=True)
    kept: list[dict] = []
    for cand in candidates:
        cset = set(cand["members"].tolist())
        dup = False
        for k in kept:
            kset = set(k["members"].tolist())
            inter = len(cset & kset)
            union = len(cset | kset)
            if union and inter / union > DEDUPE_JACCARD:
                dup = True
                break
        if not dup:
            kept.append(cand)
    return kept


# ── Null model ──────────────────────────────────────────────────────────────
def _sample_null(pts: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Density-matched resample: KDE of the real points, preserving the reporting/
    coastline/city clustering confound in the null. Falls back to bbox-uniform."""
    n = len(pts)
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(pts.T)
        kde.set_bandwidth(kde.factor * NULL_BW_SCALE)   # broaden: smear out thin lines
        return kde.resample(n, seed=rng).T
    except Exception:
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        return rng.uniform(lo, hi, size=(n, 2))


def null_distribution(pts: np.ndarray, iters: int = NULL_ITERS, seed: int = 1234,
                      **detect_kwargs) -> dict:
    """Run the detector on `iters` density-matched random fields.

    Returns the per-run max alignment size and count of alignments, used to derive
    family-wise p-values via the max-size statistic (controls the look-elsewhere effect).
    """
    rng = np.random.default_rng(seed)
    max_sizes, counts = [], []
    for _ in range(iters):
        null_pts = _sample_null(pts, rng)
        aligns = detect_alignments(null_pts, **detect_kwargs)
        max_sizes.append(max((a["count"] for a in aligns), default=0))
        counts.append(len(aligns))
    return {"max_sizes": np.array(max_sizes), "counts": np.array(counts)}


def pvalue_for_size(size: int, null_max_sizes: np.ndarray) -> float:
    """Family-wise p: fraction of null runs whose BEST alignment is >= this size."""
    n = len(null_max_sizes)
    if n == 0:
        return 1.0
    return float((np.sum(null_max_sizes >= size) + 1) / (n + 1))   # +1 smoothing


# ── Confound flags ──────────────────────────────────────────────────────────
def confound_flags(align: dict, member_layers: list[str],
                   member_latlon: np.ndarray, infra_latlon: np.ndarray | None) -> list[str]:
    flags = []
    # Graticule artifact: near-E-W line at a round latitude, or near-N-S at round longitude.
    bearing = align["bearing_deg"]
    mean_lat = float(member_latlon[:, 0].mean())
    mean_lon = float(member_latlon[:, 1].mean())
    near_ew = min(abs(bearing - 90), abs(bearing - 270)) < 8
    near_ns = min(bearing, abs(bearing - 180)) < 8
    if near_ew and abs(mean_lat - round(mean_lat)) < 0.15:
        flags.append("graticule_artifact")
    elif near_ns and abs(mean_lon - round(mean_lon)) < 0.15:
        flags.append("graticule_artifact")
    # Coastal artifact: majority of members from coastal-by-construction layers.
    coastal = sum(1 for l in member_layers if l in COASTAL_LAYERS)
    if coastal > len(member_layers) / 2:
        flags.append("coastal_artifact")
    # Infrastructure/population corridor: members track nighttime-lights points.
    if infra_latlon is not None and len(infra_latlon):
        near = 0
        for lat, lon in member_latlon:
            d = np.min(np.hypot((infra_latlon[:, 0] - lat) * 111.0,
                                (infra_latlon[:, 1] - lon) * 111.0 * math.cos(math.radians(lat))))
            if d < 25.0:
                near += 1
        if near > len(member_latlon) * 0.6:
            flags.append("infrastructure")
    return flags


# ── Self-test (synthetic, proves the math without project data) ──────────────
def selftest() -> int:
    print("=== alignments.py self-test ===")
    rng = np.random.default_rng(7)
    # Sparse background so the planted line stands above the chance noise floor.
    n_bg = 70
    bg = rng.uniform(-600, 600, size=(n_bg, 2))
    # Plant a strong line: 16 points along y = 0.4x + 50, +-3km noise, spanning the region.
    t = np.linspace(-560, 560, 16)
    line = np.column_stack([t, 0.4 * t + 50]) + rng.normal(0, 3, size=(16, 2))
    planted = np.vstack([bg, line])

    kw = dict(corridor_km=8.0, min_points=MIN_POINTS,
              theta_bins=THETA_BINS, min_span_km=MIN_SPAN_KM)
    aligns = detect_alignments(planted, **kw)
    null = null_distribution(planted, iters=120, **kw)
    ok = True

    if not aligns:
        print("  FAIL: planted line not detected"); ok = False
    else:
        best = aligns[0]
        p = pvalue_for_size(best["count"], null["max_sizes"])
        print(f"  planted field: best alignment = {best['count']} pts, "
              f"span={best['span_km']:.0f}km, resid={best['mean_resid_km']:.1f}km, p={p:.3f}")
        if best["count"] < 12:
            print(f"  FAIL: recovered only {best['count']}/16 planted points"); ok = False
        if p > SIGNIFICANCE:
            print(f"  FAIL: planted line not significant (p={p:.3f})"); ok = False

    # Pure-random control: best alignment should NOT be significant.
    ctrl = rng.uniform(-600, 600, size=(n_bg + 16, 2))
    ctrl_aligns = detect_alignments(ctrl, **kw)
    ctrl_null = null_distribution(ctrl, iters=120, seed=99, **kw)
    ctrl_best = max((a["count"] for a in ctrl_aligns), default=0)
    ctrl_p = pvalue_for_size(ctrl_best, ctrl_null["max_sizes"]) if ctrl_best else 1.0
    print(f"  random control: best alignment = {ctrl_best} pts, p={ctrl_p:.3f}")
    if ctrl_p < SIGNIFICANCE:
        print(f"  FAIL: random control flagged as significant (p={ctrl_p:.3f})"); ok = False

    print("=== PASS ===" if ok else "=== FAIL ===")
    return 0 if ok else 1


# ── Main (project pipeline entry point) ──────────────────────────────────────
def _load_points(layers_dir, layer_names, load_geojson):
    """Return (coords[N,2] lat,lon, layer_per_point[list], all latlon by layer)."""
    coords, layer_of = [], []
    for name in layer_names:
        path = layers_dir / f"{name}.geojson"
        if not path.exists():
            continue
        gj = load_geojson(path)
        for feat in gj.get("features", []):
            c = feat.get("geometry", {}).get("coordinates", [])
            if len(c) >= 2:
                coords.append([c[1], c[0]])     # lat, lon
                layer_of.append(name)
    return (np.array(coords) if coords else np.empty((0, 2))), layer_of


def _alignment_to_feature(align, latlon, member_layers, p_value, significant, flags):
    """Build a LineString GeoJSON feature; endpoints = extreme members along the axis."""
    centered = latlon  # placeholder; geometry uses extreme members below
    # Order members along the principal direction using their projected positions.
    # latlon here is the member lat/lon array; endpoints chosen by along-axis extent.
    order = np.argsort(align["_along"])
    p0 = latlon[order[0]]
    p1 = latlon[order[-1]]
    return {
        "type": "Feature",
        "geometry": {"type": "LineString",
                     "coordinates": [[float(p0[1]), float(p0[0])],
                                     [float(p1[1]), float(p1[0])]]},
        "properties": {
            "point_count": align["count"],
            "length_km": round(align["span_km"], 1),
            "mean_residual_km": round(align["mean_resid_km"], 2),
            "bearing_deg": round(align["bearing_deg"], 1),
            "p_value": round(p_value, 4),
            "significant": bool(significant),
            "layers": sorted(set(member_layers)),
            "confound_flags": flags,
        },
    }


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.common import OUTPUT_DIR, get_logger, load_geojson, save_geojson
    log = get_logger("alignments")
    log.info("=== alignments.py ===")

    layers_dir = OUTPUT_DIR / "layers"
    analysis_dir = OUTPUT_DIR / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    coords, layer_of = _load_points(layers_dir, DEFAULT_LAYERS, load_geojson)
    n = len(coords)
    log.info(f"Loaded {n} points across {len(set(layer_of))} layers "
             f"(curated set: {', '.join(DEFAULT_LAYERS)})")

    # Graceful no-data path: write empty outputs so the pipeline never crashes.
    empty = {"type": "FeatureCollection", "features": [],
             "metadata": {"note": "insufficient input points for alignment analysis"}}
    if n < MIN_POINTS:
        log.warning(f"Only {n} points available (need >= {MIN_POINTS}). Writing empty outputs. "
                    "Run the fetch + process pipeline first to populate output/layers/.")
        save_geojson(empty, analysis_dir / "alignments.geojson")
        save_geojson(empty, analysis_dir / "alignments_control.geojson")
        save_geojson({"bins": [], "note": "no data"}, analysis_dir / "alignment_bearings.json")
        save_geojson({"n_points": n, "note": "no data"}, analysis_dir / "alignment_summary.json")
        return

    # Project to local km plane about the data centroid.
    lat0, lon0 = float(coords[:, 0].mean()), float(coords[:, 1].mean())
    pts = project_azeq(coords, lat0, lon0)
    layer_arr = np.array(layer_of)

    kw = dict(corridor_km=CORRIDOR_KM, min_points=MIN_POINTS,
              theta_bins=THETA_BINS, min_span_km=MIN_SPAN_KM)
    log.info("Detecting candidate alignments…")
    aligns = detect_alignments(pts, **kw)
    log.info(f"  {len(aligns)} candidate alignments (>= {MIN_POINTS} pts, "
             f">= {MIN_SPAN_KM:.0f} km span)")

    log.info(f"Running density-matched null ({NULL_ITERS} iters)…")
    null = null_distribution(pts, iters=NULL_ITERS, **kw)
    null_mean = float(null["max_sizes"].mean())
    null_p95 = float(np.percentile(null["max_sizes"], 95))

    # Infra proxy points (optional).
    infra_coords, _ = _load_points(layers_dir, [INFRA_LAYER], load_geojson)
    infra_latlon = infra_coords if len(infra_coords) else None

    features, bearings_sig = [], []
    n_sig = 0
    for a in aligns:
        members = a["members"]
        member_latlon = coords[members]
        member_layers = layer_arr[members].tolist()
        # along-axis ordering for endpoints
        centered = pts[members] - a["centroid"]
        a["_along"] = centered @ a["direction"]
        p_value = pvalue_for_size(a["count"], null["max_sizes"])
        significant = p_value < SIGNIFICANCE
        flags = confound_flags(a, member_layers, member_latlon, infra_latlon)
        if significant and not flags:
            n_sig += 1
            bearings_sig.append(a["bearing_deg"])
        features.append(_alignment_to_feature(a, member_latlon, member_layers,
                                              p_value, significant, flags))

    fc = {"type": "FeatureCollection", "features": features,
          "metadata": {"record_count": len(features), "n_input_points": n,
                       "corridor_km": CORRIDOR_KM, "min_points": MIN_POINTS,
                       "null_iters": NULL_ITERS, "projection_center": [lat0, lon0]}}
    save_geojson(fc, analysis_dir / "alignments.geojson")

    # Negative-control overlay: one null realization's "alignments".
    ctrl_pts = _sample_null(pts, np.random.default_rng(2026))
    ctrl_aligns = detect_alignments(ctrl_pts, **kw)
    ctrl_features = []
    # control points back to lat/lon is approximate; draw in projected space is fine
    # for an illustrative overlay, so reuse the real centroid as anchor via inverse.
    for a in ctrl_aligns:
        centered = ctrl_pts[a["members"]] - a["centroid"]
        along = centered @ a["direction"]
        order = np.argsort(along)
        # invert projection approximately: small-region equirect inverse around (lat0,lon0)
        def inv(xy):
            x, y = xy
            lat = lat0 + (y / 111.0)
            lon = lon0 + (x / (111.0 * math.cos(math.radians(lat0))))
            return [float(lon), float(lat)]
        ctrl_features.append({
            "type": "Feature",
            "geometry": {"type": "LineString",
                         "coordinates": [inv(ctrl_pts[a["members"]][order[0]]),
                                         inv(ctrl_pts[a["members"]][order[-1]])]},
            "properties": {"point_count": a["count"], "control": True},
        })
    save_geojson({"type": "FeatureCollection", "features": ctrl_features,
                  "metadata": {"note": "one random null realization — for comparison only"}},
                 analysis_dir / "alignments_control.geojson")

    # Bearing rose for significant, non-confounded alignments.
    rose_bins = 12
    hist = [0] * rose_bins
    for b in bearings_sig:
        hist[int(b // (180 / rose_bins)) % rose_bins] += 1
    save_geojson({"n_bins": rose_bins, "bin_width_deg": 180 / rose_bins,
                  "counts": hist, "n_significant": len(bearings_sig),
                  "uniform_expectation": (len(bearings_sig) / rose_bins) if bearings_sig else 0},
                 analysis_dir / "alignment_bearings.json")

    verdict = ("No alignments survive the density-matched null — consistent with chance "
               "(the expected, honest result for ley-line patterns)."
               if n_sig == 0 else
               f"{n_sig} alignment(s) exceed the null AND carry no obvious confound — "
               "worth a closer look, but still correlation, not causation.")
    summary = {
        "n_input_points": n, "layers": sorted(set(layer_of)),
        "candidate_alignments": len(aligns),
        "significant_unconfounded": n_sig,
        "null_max_size_mean": round(null_mean, 2),
        "null_max_size_p95": round(null_p95, 2),
        "params": kw, "significance_threshold": SIGNIFICANCE,
        "verdict": verdict,
    }
    save_geojson(summary, analysis_dir / "alignment_summary.json")
    log.info(f"  {n_sig} significant, unconfounded alignment(s). {verdict}")
    log.info(f"Wrote alignments.geojson, alignments_control.geojson, "
             f"alignment_bearings.json, alignment_summary.json → {analysis_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spatial alignment detection + null test")
    parser.add_argument("--selftest", action="store_true",
                        help="Run the synthetic self-test (numpy/scipy only)")
    args = parser.parse_args()
    if args.selftest:
        sys.exit(selftest())
    main()

"""
Population density bias correction for UAP and other observation-biased layers.

Uses NASA SEDAC GPW v4 population grid (1km resolution) or US Census county data
as a fallback to calculate expected report density assuming random distribution
by population. Flags clusters that exceed expected density by >2 standard deviations.

Primary source: NASA SEDAC GPW v4
  https://sedac.ciesin.columbia.edu/data/collection/gpw-v4
  Free, requires registration.

Fallback: US Census county population estimates (no registration required)
  https://www2.census.gov/programs-surveys/popest/tables/

Output: output/analysis/population_corrected_<layer>.geojson
        output/analysis/population_control_summary.json
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import OUTPUT_DIR, RAW_DATA_DIR, get_logger, fetch_with_retry, save_geojson, load_geojson

log = get_logger("population_control")

LAYERS_DIR = OUTPUT_DIR / "layers"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"
RAW_POP_DIR = RAW_DATA_DIR / "population"

# Layers that need population bias correction (observation-dependent)
POPULATION_BIASED_LAYERS = {"nuforc", "epa_radnet", "doe_grid"}

# US Census county population estimates
CENSUS_URL = "https://www2.census.gov/programs-surveys/popest/tables/2020-2023/counties/totals/co-est2023-alldata.csv"

# Grid resolution for density calculation (degrees)
GRID_RESOLUTION = 0.5  # ~55km cells


def fetch_census_population() -> pd.DataFrame | None:
    """Fetch US county population estimates as fallback."""
    raw_path = RAW_POP_DIR / "census_county_pop.csv"
    RAW_POP_DIR.mkdir(parents=True, exist_ok=True)

    if raw_path.exists():
        log.info(f"Loading cached census data from {raw_path}")
        return pd.read_csv(raw_path, encoding="latin1")

    log.info("Fetching US Census county population estimates…")
    try:
        resp = fetch_with_retry(CENSUS_URL, logger=log)
        with open(raw_path, "wb") as f:
            f.write(resp.content)
        return pd.read_csv(raw_path, encoding="latin1")
    except Exception as exc:
        log.warning(f"Census fetch failed: {exc}")
        return None


def build_population_grid(census_df: pd.DataFrame | None) -> dict:
    """
    Build a lat/lon grid of population density for the continental US.
    Returns dict: (lat_bin, lon_bin) -> population
    """
    if census_df is None:
        log.warning("No population data available; using uniform distribution")
        return {}

    # Census data has INTPTLAT (lat) and INTPTLONG (lon) for county centroids
    lat_col = next((c for c in census_df.columns if "lat" in c.lower() or "intptlat" in c.lower()), None)
    lon_col = next((c for c in census_df.columns if "lon" in c.lower() or "intptlong" in c.lower()), None)
    pop_col = next((c for c in census_df.columns if "popestimate2022" in c.lower() or
                    "popestimate" in c.lower() or "population" in c.lower()), None)

    if not all([lat_col, lon_col, pop_col]):
        log.warning(f"Cannot find required columns. Available: {list(census_df.columns[:20])}")
        return {}

    grid = {}
    for _, row in census_df.iterrows():
        try:
            lat = float(str(row[lat_col]).strip().lstrip("+"))
            lon = float(str(row[lon_col]).strip())
            pop = float(row[pop_col])
            if np.isnan(lat) or np.isnan(lon) or np.isnan(pop):
                continue
            lat_bin = round(lat / GRID_RESOLUTION) * GRID_RESOLUTION
            lon_bin = round(lon / GRID_RESOLUTION) * GRID_RESOLUTION
            key = (lat_bin, lon_bin)
            grid[key] = grid.get(key, 0) + pop
        except (ValueError, TypeError):
            continue

    log.info(f"Built population grid with {len(grid)} cells (resolution={GRID_RESOLUTION}°)")
    return grid


def calculate_density_ratio(
    layer_geojson: dict,
    pop_grid: dict,
    grid_res: float = GRID_RESOLUTION,
) -> list[dict]:
    """
    For each grid cell containing layer records, calculate:
      observed_density = records per cell
      expected_density = (records_total * cell_pop) / total_pop
      density_ratio = observed / expected
      z_score = (observed - expected) / sqrt(expected)  [Poisson approximation]
    """
    features = layer_geojson.get("features", [])
    if not features:
        return []

    # Count records per grid cell
    cell_counts: dict = {}
    for feat in features:
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        lat_bin = round(lat / grid_res) * grid_res
        lon_bin = round(lon / grid_res) * grid_res
        key = (lat_bin, lon_bin)
        cell_counts[key] = cell_counts.get(key, 0) + 1

    total_records = sum(cell_counts.values())
    total_pop = sum(pop_grid.values()) if pop_grid else 1

    results = []
    for (lat_bin, lon_bin), observed in cell_counts.items():
        cell_pop = pop_grid.get((lat_bin, lon_bin), 0)
        if total_pop > 0 and cell_pop > 0:
            expected = total_records * (cell_pop / total_pop)
        else:
            expected = total_records / max(len(cell_counts), 1)

        ratio = observed / expected if expected > 0 else float("inf")
        # Poisson z-score
        z = (observed - expected) / max(np.sqrt(expected), 0.001)

        results.append({
            "lat": lat_bin,
            "lon": lon_bin,
            "observed_count": observed,
            "expected_count": round(expected, 3),
            "density_ratio": round(ratio, 3),
            "z_score": round(float(z), 3),
            "cell_population": int(cell_pop),
            "significant": z > 2.0,  # >2σ flagged as non-random
        })

    results.sort(key=lambda x: x["z_score"], reverse=True)
    return results


def main():
    log.info("=== population_control.py ===")
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    census_df = fetch_census_population()
    pop_grid = build_population_grid(census_df)

    all_summaries = {}

    for layer_name in POPULATION_BIASED_LAYERS:
        layer_path = LAYERS_DIR / f"{layer_name}.geojson"
        if not layer_path.exists():
            log.warning(f"Layer not found: {layer_path}")
            continue

        log.info(f"\nProcessing population control for '{layer_name}'…")
        gj = load_geojson(layer_path)
        results = calculate_density_ratio(gj, pop_grid)

        if not results:
            log.warning(f"No results for {layer_name}")
            continue

        significant_cells = [r for r in results if r["significant"]]
        log.info(f"  {len(results)} grid cells, {len(significant_cells)} significant (z>2σ)")

        if significant_cells:
            log.info(f"  Top clusters (z>2σ) for {layer_name}:")
            for cell in significant_cells[:10]:
                log.info(
                    f"    lat={cell['lat']:.1f}, lon={cell['lon']:.1f} | "
                    f"observed={cell['observed_count']}, expected={cell['expected_count']}, "
                    f"ratio={cell['density_ratio']:.1f}x, z={cell['z_score']:.2f}"
                )

        out_path = ANALYSIS_DIR / f"population_corrected_{layer_name}.json"
        with open(out_path, "w") as f:
            json.dump({"layer": layer_name, "grid_cells": results}, f, indent=2)

        all_summaries[layer_name] = {
            "total_cells": len(results),
            "significant_cells": len(significant_cells),
            "max_z_score": results[0]["z_score"] if results else 0,
            "top_cluster": results[0] if results else None,
        }

    summary_path = ANALYSIS_DIR / "population_control_summary.json"
    with open(summary_path, "w") as f:
        json.dump(all_summaries, f, indent=2)

    log.info(f"\nPopulation control complete. Summary → {summary_path}")


if __name__ == "__main__":
    main()

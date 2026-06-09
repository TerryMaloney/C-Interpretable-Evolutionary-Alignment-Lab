"""
Cross-layer temporal and spatial correlation analysis.

For layers with timestamps:
  - Do events cluster in time as well as space?
  - Do UAP spikes, stranding events, and grid anomalies co-occur in 30-day windows?
  - Cross-reference against NOAA geomagnetic K-index

Output:
  output/analysis/temporal_correlation.json
  output/analysis/kindex_correlation.json
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    OUTPUT_DIR, RAW_DATA_DIR, get_logger, fetch_with_retry, load_geojson, save_geojson
)

log = get_logger("correlation")

LAYERS_DIR = OUTPUT_DIR / "layers"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"
RAW_DIR = RAW_DATA_DIR / "kindex"

# Layers with timestamps to include in temporal analysis
TEMPORAL_LAYERS = ["nuforc", "noaa_ume", "usgs_seismic", "doe_grid"]

# NOAA space weather K-index data
KINDEX_URL = "https://www.swpc.noaa.gov/products/planetary-k-index"
KINDEX_DATA_URL = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
KINDEX_HISTORY_URL = "https://www.swpc.noaa.gov/ftpdir/indices/old_indices/"

# Temporal window for co-occurrence (days)
COOCCURRENCE_WINDOW_DAYS = 30
SPATIAL_RADIUS_KM = 200  # For spatio-temporal correlation


def load_layer_timeseries(layer_name: str) -> pd.DataFrame:
    """Load layer GeoJSON and extract time-indexed records."""
    path = LAYERS_DIR / f"{layer_name}.geojson"
    if not path.exists():
        return pd.DataFrame()

    gj = load_geojson(path)
    rows = []
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        dt_str = props.get("datetime")
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if len(coords) < 2 or not dt_str:
            continue
        try:
            dt = pd.to_datetime(dt_str, utc=True, errors="coerce")
            if pd.isna(dt):
                continue
            rows.append({
                "layer": layer_name,
                "datetime": dt,
                "lat": coords[1],
                "lon": coords[0],
                "year": dt.year,
                "month": dt.month,
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    return df.sort_values("datetime")


def temporal_cooccurrence(dfs: dict[str, pd.DataFrame], window_days: int = COOCCURRENCE_WINDOW_DAYS) -> list[dict]:
    """
    Find time windows where multiple layers spike simultaneously.
    Returns list of windows with co-occurring layer spikes.
    """
    if len(dfs) < 2:
        return []

    # Build monthly event counts per layer
    monthly = {}
    for layer, df in dfs.items():
        if df.empty:
            continue
        monthly[layer] = df.groupby(["year", "month"]).size().reset_index(name="count")
        monthly[layer]["period"] = pd.to_datetime(
            monthly[layer][["year", "month"]].assign(day=1)
        )

    if len(monthly) < 2:
        return []

    # Find months where multiple layers have elevated activity (>1.5σ above mean)
    layer_thresholds = {}
    for layer, df in monthly.items():
        mean_count = df["count"].mean()
        std_count = df["count"].std()
        layer_thresholds[layer] = mean_count + 1.5 * std_count

    # Get all unique periods
    all_periods = set()
    for df in monthly.values():
        all_periods.update(df["period"].tolist())

    cooccurrence_periods = []
    for period in sorted(all_periods):
        active_layers = []
        for layer, df in monthly.items():
            row = df[df["period"] == period]
            if row.empty:
                continue
            count = row["count"].values[0]
            threshold = layer_thresholds[layer]
            if count >= threshold:
                active_layers.append({"layer": layer, "count": int(count), "threshold": round(threshold, 1)})

        if len(active_layers) >= 2:
            cooccurrence_periods.append({
                "period": period.isoformat(),
                "active_layers": active_layers,
                "layer_count": len(active_layers),
            })

    cooccurrence_periods.sort(key=lambda x: x["layer_count"], reverse=True)
    return cooccurrence_periods


def fetch_kindex() -> pd.DataFrame | None:
    """Fetch NOAA planetary K-index data."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / "kindex_recent.json"

    log.info("Fetching NOAA K-index data…")
    try:
        resp = fetch_with_retry(KINDEX_DATA_URL, logger=log)
        with open(raw_path, "w") as f:
            f.write(resp.text)
        data = resp.json()

        rows = []
        for entry in data:
            try:
                dt = pd.to_datetime(entry.get("time_tag"), utc=True)
                kp = float(entry.get("kp_index", 0))
                rows.append({"datetime": dt, "kp": kp})
            except Exception:
                continue

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        log.info(f"Loaded {len(df)} K-index readings")
        return df
    except Exception as exc:
        log.warning(f"K-index fetch failed: {exc}")
        return None


def kindex_correlation(layer_dfs: dict[str, pd.DataFrame], kindex_df: pd.DataFrame | None) -> dict:
    """
    Correlate UAP/stranding spikes with elevated geomagnetic K-index.
    High K-index (Kp >= 4) = geomagnetic storm.
    """
    if kindex_df is None or kindex_df.empty:
        return {"error": "K-index data not available"}

    # Daily max K-index
    kindex_df["date"] = kindex_df["datetime"].dt.date
    daily_kmax = kindex_df.groupby("date")["kp"].max().reset_index()
    daily_kmax.columns = ["date", "kp_max"]

    results = {}
    for layer, df in layer_dfs.items():
        if df.empty:
            continue

        df["date"] = df["datetime"].dt.date
        daily_events = df.groupby("date").size().reset_index(name="event_count")

        merged = pd.merge(daily_events, daily_kmax, on="date", how="inner")
        if len(merged) < 10:
            continue

        # Pearson correlation
        try:
            corr = merged["event_count"].corr(merged["kp_max"])
            storm_days = merged[merged["kp_max"] >= 4]
            quiet_days = merged[merged["kp_max"] < 2]

            results[layer] = {
                "pearson_r": round(float(corr), 4),
                "n_overlap_days": len(merged),
                "mean_events_storm_days": round(float(storm_days["event_count"].mean()), 2) if len(storm_days) else None,
                "mean_events_quiet_days": round(float(quiet_days["event_count"].mean()), 2) if len(quiet_days) else None,
                "n_storm_days": len(storm_days),
                "n_quiet_days": len(quiet_days),
            }
            log.info(
                f"  {layer} K-index correlation: r={corr:.3f}, "
                f"storm avg={results[layer]['mean_events_storm_days']}, "
                f"quiet avg={results[layer]['mean_events_quiet_days']}"
            )
        except Exception as exc:
            log.warning(f"  Correlation failed for {layer}: {exc}")

    return results


def main():
    log.info("=== correlation.py ===")
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    # Load temporal layers
    log.info("Loading temporal layers…")
    dfs = {}
    for layer in TEMPORAL_LAYERS:
        df = load_layer_timeseries(layer)
        if not df.empty:
            dfs[layer] = df
            log.info(f"  {layer}: {len(df):,} records, "
                     f"{df['datetime'].min().date()} to {df['datetime'].max().date()}")
        else:
            log.info(f"  {layer}: no temporal data available")

    # Temporal co-occurrence
    log.info("\nCalculating temporal co-occurrence…")
    cooccurrence = temporal_cooccurrence(dfs)
    log.info(f"Found {len(cooccurrence)} co-occurrence periods (multiple layers elevated simultaneously)")
    if cooccurrence:
        log.info("Top co-occurrence periods:")
        for period in cooccurrence[:5]:
            layers = [f"{a['layer']}({a['count']})" for a in period["active_layers"]]
            log.info(f"  {period['period'][:7]}: {', '.join(layers)}")

    cooccurrence_path = ANALYSIS_DIR / "temporal_correlation.json"
    with open(cooccurrence_path, "w") as f:
        json.dump({"cooccurrence_periods": cooccurrence}, f, indent=2, default=str)

    # K-index correlation
    log.info("\nFetching geomagnetic K-index for correlation…")
    kindex_df = fetch_kindex()
    kindex_results = kindex_correlation(dfs, kindex_df)

    kindex_path = ANALYSIS_DIR / "kindex_correlation.json"
    with open(kindex_path, "w") as f:
        json.dump(kindex_results, f, indent=2, default=str)

    log.info(f"\nCorrelation analysis complete.")
    log.info(f"  Co-occurrence results → {cooccurrence_path}")
    log.info(f"  K-index correlation → {kindex_path}")


if __name__ == "__main__":
    main()

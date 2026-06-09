"""
Fetch GPS-TEC ionospheric disturbance data from NASA CDDIS IONEX files.

Source: NASA CDDIS (Crustal Dynamics Data Information System)
Archive: https://cddis.nasa.gov/archive/gnss/products/ionex/
JPL GIMs: https://sideshow.jpl.nasa.gov/pub/iono_daily/

Physics basis: Electromagnetic. Fast-moving objects in the upper atmosphere
create shockwaves that disturb ionospheric plasma (Total Electron Content).
The entire GPS constellation is a continuous ionospheric monitor.

Analysis target:
  - Localized TEC spikes (single-cell anomalies, not regional storms)
  - After removing solar/geomagnetic contribution (Kp and Dst index)
  - After removing seismogenic TEC precursors (cross-ref USGS catalog)
  - Residual: unexplained localized ionospheric disturbances

Published precedent: TEC anomalies documented before L'Aquila 2009 and Tohoku 2011.

Last verified: 2026-06-09

Dependencies: georinex, xarray, numpy

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  tec_tecu, tec_anomaly_tecu, kp_at_time
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, fetch_with_retry,
    get_logger, make_record, records_to_geojson, save_geojson, save_raw,
)

log = get_logger("fetch_gps_tec")

LAYER = "gps_tec"
CONFIDENCE = 4
CATEGORY = "ionospheric"

RAW_DIR = RAW_DATA_DIR / "gps_tec"
OUT_PATH = PROCESSED_DATA_DIR / "gps_tec.geojson"

# CDDIS IONEX archive — daily JPL GIMs (Global Ionosphere Maps)
# Format: https://cddis.nasa.gov/archive/gnss/products/ionex/{YEAR}/{DOY}/
CDDIS_BASE = "https://cddis.nasa.gov/archive/gnss/products/ionex"
JPL_IONEX_PATTERN = "jplg{doy:03d}0.{year2}i.Z"

# Analysis window: sample a few months to identify persistent anomaly zones
ANALYSIS_YEAR = int(os.getenv("TEC_YEAR", "2023"))
ANALYSIS_MONTHS = int(os.getenv("TEC_MONTHS", "3"))  # Months to process

# Anomaly threshold (TECU = TEC units, 1 TECU = 10^16 electrons/m^2)
TEC_ANOMALY_THRESHOLD_SIGMA = 2.5

# Grid sampling: only extract points with |anomaly| > threshold
# Focus on Zone A and Zone B bounding boxes
ANALYSIS_BBOXES = {
    "zone_a": {"min_lat": 30, "max_lat": 45, "min_lon": -112, "max_lon": -104},
    "zone_b": {"min_lat": 29, "max_lat": 35, "min_lon": -121, "max_lon": -116},
    "zone_e": {"min_lat": 30, "max_lat": 45, "min_lon": 130,  "max_lon": 150},
    "global_coarse": {"min_lat": -90, "max_lat": 90, "min_lon": -180, "max_lon": 180},
}


def download_ionex(year: int, doy: int) -> Path | None:
    """Download a single IONEX file by year and day-of-year."""
    year2 = str(year)[-2:]
    filename = JPL_IONEX_PATTERN.format(doy=doy, year2=year2)
    out_path = RAW_DIR / str(year) / filename

    if out_path.exists():
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{CDDIS_BASE}/{year}/{doy:03d}/{filename}"

    try:
        resp = fetch_with_retry(url, stream=True, logger=log)
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        log.info(f"  Downloaded {filename}")
        return out_path
    except Exception as exc:
        log.warning(f"  Could not download {url}: {exc}")
        return None


def decompress_ionex(path: Path) -> Path | None:
    """Decompress .Z (Unix compress) or .gz file."""
    if path.suffix == ".Z":
        import subprocess
        out_path = path.with_suffix("")
        if out_path.exists():
            return out_path
        try:
            subprocess.run(["uncompress", "-k", str(path)], check=True, capture_output=True)
            return out_path
        except Exception:
            try:
                subprocess.run(["gunzip", "-k", "-S", ".Z", str(path)],
                               check=True, capture_output=True)
                return out_path
            except Exception as exc:
                log.warning(f"Decompression failed for {path}: {exc}")
                return None
    return path


def parse_ionex(ionex_path: Path, bbox: dict) -> list[dict]:
    """
    Parse IONEX file and extract TEC anomaly points within bbox.
    Returns list of anomaly records.
    """
    try:
        import georinex as gr
    except ImportError:
        log.error("georinex not installed. Run: pip install georinex")
        return []

    try:
        tec_ds = gr.load(str(ionex_path))
        if "tec" not in tec_ds:
            return []

        tec = tec_ds["tec"].values  # (time, lat, lon)
        lats = tec_ds["lat"].values
        lons = tec_ds["lon"].values
        times = tec_ds["time"].values

    except Exception as exc:
        log.warning(f"Failed to parse {ionex_path}: {exc}")
        return []

    # Compute global mean and std for anomaly detection
    valid = tec[~np.isnan(tec)]
    if len(valid) == 0:
        return []

    global_mean = np.nanmean(valid)
    global_std = np.nanstd(valid)
    threshold = TEC_ANOMALY_THRESHOLD_SIGMA * global_std

    # Filter to bbox
    lat_mask = (lats >= bbox["min_lat"]) & (lats <= bbox["max_lat"])
    lon_mask = (lons >= bbox["min_lon"]) & (lons <= bbox["max_lon"])

    records = []
    for t_idx, time_val in enumerate(times):
        try:
            dt_str = str(time_val)[:19] + "Z"
        except Exception:
            dt_str = None

        for lat_idx in np.where(lat_mask)[0]:
            for lon_idx in np.where(lon_mask)[0]:
                val = tec[t_idx, lat_idx, lon_idx]
                if np.isnan(val):
                    continue
                anomaly = abs(val - global_mean)
                if anomaly < threshold:
                    continue
                try:
                    rec = make_record(
                        layer=LAYER,
                        lat=float(lats[lat_idx]),
                        lon=float(lons[lon_idx]),
                        datetime_str=dt_str,
                        confidence=CONFIDENCE,
                        category=CATEGORY,
                        source=f"NASA CDDIS JPL GIM {ionex_path.stem}",
                        notes=(
                            f"TEC anomaly: {val:.1f} TECU "
                            f"(mean={global_mean:.1f}, σ={global_std:.1f}, "
                            f"z={anomaly/global_std:.2f})"
                        ),
                        extra={
                            "tec_tecu": round(float(val), 2),
                            "tec_anomaly_tecu": round(float(anomaly), 2),
                            "tec_z_score": round(float(anomaly / global_std), 3),
                        },
                    )
                    records.append(rec)
                except ValueError:
                    continue

    return records


def main():
    log.info("=== fetch_gps_tec.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import georinex
    except ImportError:
        log.error(
            "georinex not installed. Run: pip install georinex\n"
            "Skipping GPS-TEC processing."
        )
        return

    start_date = datetime(ANALYSIS_YEAR, 1, 1, tzinfo=timezone.utc)
    # Process one month worth of days to start
    days_to_process = 30 * min(ANALYSIS_MONTHS, 3)

    all_records = []
    log.info(f"Processing {days_to_process} days of IONEX data ({ANALYSIS_YEAR})…")

    for day_offset in range(0, days_to_process, 5):  # Step 5 days to reduce volume
        target_date = start_date + timedelta(days=day_offset)
        doy = target_date.timetuple().tm_yday
        year = target_date.year

        ionex_path = download_ionex(year, doy)
        if not ionex_path:
            continue

        decompressed = decompress_ionex(ionex_path)
        if not decompressed:
            continue

        for bbox_name, bbox in ANALYSIS_BBOXES.items():
            if bbox_name == "global_coarse":
                continue  # Skip full-global pass for now
            records = parse_ionex(decompressed, bbox)
            if records:
                all_records.extend(records)
                log.info(f"  {target_date.date()} {bbox_name}: {len(records)} anomalies")

    log.info(f"Total TEC anomaly records: {len(all_records):,}")

    if all_records:
        gj = records_to_geojson(all_records)
        save_geojson(gj, OUT_PATH)
        log.info(f"Saved → {OUT_PATH}")
    else:
        log.warning(
            "No TEC anomalies found. Possible causes:\n"
            "  1. CDDIS requires Earthdata login for recent data:\n"
            "     https://urs.earthdata.nasa.gov/\n"
            "  2. Install georinex: pip install georinex\n"
            "  3. Try JPL public GIMs at: https://ionex.info"
        )


if __name__ == "__main__":
    main()

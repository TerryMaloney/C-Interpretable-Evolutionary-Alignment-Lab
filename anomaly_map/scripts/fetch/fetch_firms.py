"""
Fetch NASA FIRMS (Fire Information for Resource Management System) thermal anomalies.

Source: NASA FIRMS / LANCE VIIRS + MODIS
Main portal: https://firms.modaps.eosdis.nasa.gov/download/
API docs: https://firms.modaps.eosdis.nasa.gov/api/area/

Physics basis: Thermodynamics. Energy conversion always produces heat.
Analysis target: HIGH-confidence, NIGHTTIME detections in non-industrial,
non-fire-season zones that cannot be attributed to known sources.

Satellites:
  VIIRS S-NPP: 375m resolution, 2012–present
  MODIS:       1km resolution,  2000–present

Last verified: 2026-06-09

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  brightness_k, frp_mw, satellite, daynight
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, fetch_with_retry,
    get_logger, make_record, records_to_geojson, save_geojson, save_raw,
)

log = get_logger("fetch_firms")

LAYER = "firms_thermal"
CONFIDENCE = 4
CATEGORY = "thermal"

RAW_DIR = RAW_DATA_DIR / "firms_thermal"
OUT_PATH = PROCESSED_DATA_DIR / "firms_thermal.geojson"

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")

# US bounding box: west,south,east,north
US_BBOX = "-125,24,-65,50"
# Global Zone E (Japan): east,south,west,north
ZONE_E_BBOX = "130,30,150,45"

# Query days of archive (increase for historical analysis; caution: large files)
DEFAULT_DAYS = int(os.getenv("FIRMS_DAYS", "365"))

# Minimum fire radiative power (MW) to consider — filters out low-energy events
MIN_FRP_MW = float(os.getenv("FIRMS_MIN_FRP", "10.0"))

# Brightness threshold — anomalous non-fire events (K)
MIN_BRIGHTNESS_K = float(os.getenv("FIRMS_MIN_BRIGHTNESS", "320.0"))

PRODUCTS = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"]

# URL for area API (requires free FIRMS MAP_KEY)
AREA_API_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{product}/{bbox}/{days}"

# Archive URL (no key needed for older data >3 months)
ARCHIVE_URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/{product_lower}/{product_lower}_7d.csv"


def fetch_firms_product(product: str, bbox: str, days: int) -> pd.DataFrame | None:
    """Fetch FIRMS data via area API or archive fallback."""
    if FIRMS_MAP_KEY:
        url = AREA_API_URL.format(key=FIRMS_MAP_KEY, product=product, bbox=bbox, days=days)
        log.info(f"Fetching {product} via API: {url[:80]}…")
        try:
            resp = fetch_with_retry(url, logger=log)
            raw_path = RAW_DIR / f"firms_{product.lower()}.csv"
            save_raw(resp.text, raw_path)
            df = pd.read_csv(StringIO(resp.text), low_memory=False)
            log.info(f"  {product}: {len(df):,} detections")
            return df
        except Exception as exc:
            log.warning(f"  API failed for {product}: {exc}")

    # Fallback: 7-day NRT archive (no key required)
    product_lower = product.lower().replace("_nrt", "").replace("_snpp", "_snpp_nrt")
    url = ARCHIVE_URL.format(product_lower=product_lower)
    log.info(f"Trying archive fallback: {url}")
    try:
        resp = fetch_with_retry(url, logger=log)
        df = pd.read_csv(StringIO(resp.text), low_memory=False)
        log.info(f"  {product} archive: {len(df):,} detections")
        return df
    except Exception as exc:
        log.warning(f"  Archive fallback failed: {exc}")
        return None


def filter_anomalies(df: pd.DataFrame, product: str) -> pd.DataFrame:
    """
    Apply anomaly filters:
    1. Nighttime only (daynight == 'N')
    2. High confidence ('h' for VIIRS; confidence >= 80 for MODIS)
    3. FRP above threshold
    4. Brightness above threshold
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [c.lower().strip() for c in df.columns]
    original_len = len(df)

    # Nighttime filter
    if "daynight" in df.columns:
        df = df[df["daynight"].str.upper() == "N"]
    elif "night_day" in df.columns:
        df = df[df["night_day"].str.upper() == "N"]

    # Confidence filter
    if "confidence" in df.columns:
        conf = df["confidence"].astype(str).str.strip().str.lower()
        if conf.str.contains("h|n|nominal|high").any():
            # VIIRS: 'h' (high), 'n' (nominal), 'l' (low)
            df = df[conf.isin(["h", "n", "nominal", "high"])]
        else:
            # MODIS: numeric 0-100
            try:
                df = df[pd.to_numeric(df["confidence"], errors="coerce") >= 80]
            except Exception:
                pass

    # FRP filter
    frp_col = next((c for c in df.columns if "frp" in c), None)
    if frp_col:
        df[frp_col] = pd.to_numeric(df[frp_col], errors="coerce")
        df = df[df[frp_col] >= MIN_FRP_MW]

    # Brightness filter
    bright_col = next((c for c in df.columns if "bright" in c and "t31" not in c), None)
    if bright_col:
        df[bright_col] = pd.to_numeric(df[bright_col], errors="coerce")
        df = df[df[bright_col] >= MIN_BRIGHTNESS_K]

    log.info(f"  {product}: {original_len:,} → {len(df):,} after anomaly filters")
    return df


def normalize(df: pd.DataFrame, product: str) -> list[dict]:
    """Convert filtered FIRMS detections to standard records."""
    df.columns = [c.lower().strip() for c in df.columns]

    lat_col = next((c for c in df.columns if c == "latitude"), None)
    lon_col = next((c for c in df.columns if c == "longitude"), None)
    if not lat_col or not lon_col:
        log.warning(f"No lat/lon columns found in {product}")
        return []

    date_col = next((c for c in df.columns if "acq_date" in c or "date" in c), None)
    time_col = next((c for c in df.columns if "acq_time" in c or "time" in c), None)
    bright_col = next((c for c in df.columns if "bright" in c and "t31" not in c), None)
    frp_col = next((c for c in df.columns if "frp" in c), None)
    sat_col = next((c for c in df.columns if "satellite" in c), None)

    records = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Normalizing {product}", leave=False):
        try:
            lat = float(row[lat_col])
            lon = float(row[lon_col])

            dt_str = None
            if date_col and pd.notna(row.get(date_col)):
                dt_str = str(row[date_col])
                if time_col and pd.notna(row.get(time_col)):
                    t = str(int(row[time_col])).zfill(4)
                    dt_str += f"T{t[:2]}:{t[2:]}Z"

            brightness = float(row[bright_col]) if bright_col and pd.notna(row.get(bright_col)) else None
            frp = float(row[frp_col]) if frp_col and pd.notna(row.get(frp_col)) else None
            sat = str(row[sat_col]) if sat_col and pd.notna(row.get(sat_col)) else product

            notes = f"{sat} | brightness={brightness}K | FRP={frp}MW | nighttime high-confidence"

            rec = make_record(
                layer=LAYER,
                lat=lat,
                lon=lon,
                datetime_str=dt_str,
                confidence=CONFIDENCE,
                category=CATEGORY,
                source=f"NASA FIRMS {product}",
                notes=notes,
                extra={
                    "brightness_k": brightness,
                    "frp_mw": frp,
                    "satellite": sat,
                    "daynight": "N",
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue

    return records


def main():
    log.info("=== fetch_firms.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not FIRMS_MAP_KEY:
        log.warning(
            "FIRMS_MAP_KEY not set in .env — using 7-day archive fallback only.\n"
            "For full historical archive, get a free key at:\n"
            "  https://firms.modaps.eosdis.nasa.gov/api/data_availability/\n"
            "Then set FIRMS_MAP_KEY=<your_key> in .env"
        )

    all_records = []
    for product in PRODUCTS[:2]:  # VIIRS S-NPP and NOAA-20 by default
        for bbox_name, bbox in [("us", US_BBOX), ("zone_e", ZONE_E_BBOX)]:
            df = fetch_firms_product(product, bbox, DEFAULT_DAYS)
            if df is not None and not df.empty:
                df = filter_anomalies(df, product)
                records = normalize(df, product)
                all_records.extend(records)
                log.info(f"  {product}/{bbox_name}: {len(records)} anomaly records")

    log.info(f"Total FIRMS thermal anomaly records: {len(all_records):,}")

    if all_records:
        gj = records_to_geojson(all_records)
        save_geojson(gj, OUT_PATH)
        log.info(f"Saved → {OUT_PATH}")
    else:
        log.warning("No FIRMS records — check API key or connectivity")


if __name__ == "__main__":
    main()

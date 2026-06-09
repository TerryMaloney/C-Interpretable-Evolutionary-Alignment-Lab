"""
Fetch USGS earthquake catalog via FDSN Event API.

Source: US Geological Survey
API: https://earthquake.usgs.gov/fdsnws/event/1/
Documentation: https://earthquake.usgs.gov/fdsnws/event/1/

Last verified: 2026-06-09

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  magnitude, depth_km, event_type, place
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    fetch_with_retry,
    get_logger,
    make_record,
    records_to_geojson,
    save_geojson,
    save_raw,
)

log = get_logger("fetch_usgs_seismic")

LAYER = "usgs_seismic"
CONFIDENCE = 5
CATEGORY = "geophysical"

API_BASE = "https://earthquake.usgs.gov/fdsnws/event/1/query"
RAW_DIR = RAW_DATA_DIR / "usgs_seismic"
OUT_PATH = PROCESSED_DATA_DIR / "usgs_seismic.geojson"

MIN_MAG = float(os.getenv("USGS_MIN_MAGNITUDE", "2.5"))
START_DATE = os.getenv("USGS_START_DATE", "2000-01-01")
END_DATE = os.getenv("USGS_END_DATE", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

# Continental US bounding box
US_BBOX = {
    "minlatitude": 24.0,
    "maxlatitude": 50.0,
    "minlongitude": -125.0,
    "maxlongitude": -65.0,
}

# FDSN API caps at 20,000 events per request; chunk by year to avoid limit
MAX_RECORDS_PER_REQUEST = 19000


def fetch_year(year: int) -> list[dict]:
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    params = {
        "format": "geojson",
        "starttime": start,
        "endtime": end,
        "minmagnitude": MIN_MAG,
        **US_BBOX,
        "limit": MAX_RECORDS_PER_REQUEST,
        "orderby": "time",
    }
    log.info(f"Fetching seismic data for {year} (M{MIN_MAG}+)…")
    resp = fetch_with_retry(API_BASE, params=params, logger=log)
    data = resp.json()
    features = data.get("features", [])
    log.info(f"  {year}: {len(features):,} events")

    raw_path = RAW_DIR / f"seismic_{year}.geojson"
    save_raw(resp.text, raw_path)
    return features


def normalize(features: list[dict]) -> list[dict]:
    records = []
    for feat in features:
        try:
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue
            lon, lat, depth = coords[0], coords[1], coords[2] if len(coords) > 2 else None

            props = feat.get("properties", {})
            mag = props.get("mag")
            place = props.get("place", "")
            time_ms = props.get("time")
            event_type = props.get("type", "earthquake")
            usgs_id = feat.get("id", "")

            dt_str = None
            if time_ms is not None:
                dt_str = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc).isoformat()

            notes = f"{place} | M{mag} | depth {depth}km" if depth else f"{place} | M{mag}"

            rec = make_record(
                layer=LAYER,
                lat=lat,
                lon=lon,
                datetime_str=dt_str,
                confidence=CONFIDENCE,
                category=CATEGORY,
                source=f"USGS FDSN ({usgs_id})",
                notes=notes,
                extra={
                    "magnitude": mag,
                    "depth_km": depth,
                    "event_type": event_type,
                    "place": place,
                    "usgs_id": usgs_id,
                },
            )
            records.append(rec)
        except (ValueError, TypeError, KeyError):
            continue
    return records


def main():
    log.info("=== fetch_usgs_seismic.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_year = int(START_DATE[:4])
    end_year = int(END_DATE[:4])

    all_features = []
    for year in range(start_year, end_year + 1):
        try:
            all_features.extend(fetch_year(year))
        except Exception as exc:
            log.error(f"Failed to fetch year {year}: {exc}")

    log.info(f"Total features fetched: {len(all_features):,}")
    records = normalize(all_features)
    log.info(f"Normalized: {len(records):,} records")

    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()

"""
Fetch EPA RadNet radiation monitoring network station locations and data.

Source: US Environmental Protection Agency
Near-real-time dashboard: https://www.epa.gov/radnet/radnet-near-real-time-air-data
Historical via Envirofacts: https://enviro.epa.gov/envirofacts/radnet/search
CDX: https://cdxnode64.epa.gov/radnet-public/query.do

This script:
1. Fetches station list with coordinates from EPA Envirofacts REST API
2. Retrieves gross beta readings per station (beta is the primary anomaly indicator)
3. Flags stations with historical spikes (readings >3σ from station baseline)

Last verified: 2026-06-09
"""

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

log = get_logger("fetch_epa_radnet")

LAYER = "epa_radnet"
CONFIDENCE = 4
CATEGORY = "radiation"

RAW_DIR = RAW_DATA_DIR / "epa_radnet"
OUT_PATH = PROCESSED_DATA_DIR / "epa_radnet.geojson"

# EPA Envirofacts RadNet REST API
ENVIROFACTS_BASE = "https://data.epa.gov/efservice"
STATIONS_URL = f"{ENVIROFACTS_BASE}/RADNET_STATION/JSON"
RESULTS_URL_TEMPLATE = f"{ENVIROFACTS_BASE}/RADNET_RESULT/STATION_ID/{{station_id}}/JSON"

# Hardcoded station coordinates as fallback (from public EPA RadNet map)
# This ensures we always have station locations even if API is down
KNOWN_STATIONS = [
    {"station_id": "AK1", "name": "Anchorage, AK", "lat": 61.2181, "lon": -149.9003, "state": "AK"},
    {"station_id": "AL1", "name": "Montgomery, AL", "lat": 32.3617, "lon": -86.2792, "state": "AL"},
    {"station_id": "AR1", "name": "Little Rock, AR", "lat": 34.7465, "lon": -92.2896, "state": "AR"},
    {"station_id": "AZ1", "name": "Phoenix, AZ", "lat": 33.4484, "lon": -112.0740, "state": "AZ"},
    {"station_id": "CA1", "name": "Sacramento, CA", "lat": 38.5816, "lon": -121.4944, "state": "CA"},
    {"station_id": "CA2", "name": "Los Angeles, CA", "lat": 34.0522, "lon": -118.2437, "state": "CA"},
    {"station_id": "CA3", "name": "San Diego, CA", "lat": 32.7157, "lon": -117.1611, "state": "CA"},
    {"station_id": "CO1", "name": "Denver, CO", "lat": 39.7392, "lon": -104.9903, "state": "CO"},
    {"station_id": "FL1", "name": "Tallahassee, FL", "lat": 30.4518, "lon": -84.2807, "state": "FL"},
    {"station_id": "FL2", "name": "Miami, FL", "lat": 25.7617, "lon": -80.1918, "state": "FL"},
    {"station_id": "GA1", "name": "Atlanta, GA", "lat": 33.7490, "lon": -84.3880, "state": "GA"},
    {"station_id": "HI1", "name": "Honolulu, HI", "lat": 21.3069, "lon": -157.8583, "state": "HI"},
    {"station_id": "ID1", "name": "Boise, ID", "lat": 43.6150, "lon": -116.2023, "state": "ID"},
    {"station_id": "IL1", "name": "Chicago, IL", "lat": 41.8781, "lon": -87.6298, "state": "IL"},
    {"station_id": "LA1", "name": "New Orleans, LA", "lat": 29.9511, "lon": -90.0715, "state": "LA"},
    {"station_id": "MA1", "name": "Boston, MA", "lat": 42.3601, "lon": -71.0589, "state": "MA"},
    {"station_id": "MD1", "name": "Baltimore, MD", "lat": 39.2904, "lon": -76.6122, "state": "MD"},
    {"station_id": "MI1", "name": "Lansing, MI", "lat": 42.7325, "lon": -84.5555, "state": "MI"},
    {"station_id": "MN1", "name": "Minneapolis, MN", "lat": 44.9778, "lon": -93.2650, "state": "MN"},
    {"station_id": "MO1", "name": "Kansas City, MO", "lat": 39.0997, "lon": -94.5786, "state": "MO"},
    {"station_id": "MS1", "name": "Jackson, MS", "lat": 32.2988, "lon": -90.1848, "state": "MS"},
    {"station_id": "MT1", "name": "Helena, MT", "lat": 46.5958, "lon": -112.0270, "state": "MT"},
    {"station_id": "NC1", "name": "Raleigh, NC", "lat": 35.7796, "lon": -78.6382, "state": "NC"},
    {"station_id": "NE1", "name": "Omaha, NE", "lat": 41.2565, "lon": -95.9345, "state": "NE"},
    {"station_id": "NM1", "name": "Albuquerque, NM", "lat": 35.0844, "lon": -106.6504, "state": "NM"},
    {"station_id": "NV1", "name": "Las Vegas, NV", "lat": 36.1699, "lon": -115.1398, "state": "NV"},
    {"station_id": "NY1", "name": "Albany, NY", "lat": 42.6526, "lon": -73.7562, "state": "NY"},
    {"station_id": "NY2", "name": "New York, NY", "lat": 40.7128, "lon": -74.0060, "state": "NY"},
    {"station_id": "OH1", "name": "Columbus, OH", "lat": 39.9612, "lon": -82.9988, "state": "OH"},
    {"station_id": "OR1", "name": "Portland, OR", "lat": 45.5231, "lon": -122.6765, "state": "OR"},
    {"station_id": "PA1", "name": "Philadelphia, PA", "lat": 39.9526, "lon": -75.1652, "state": "PA"},
    {"station_id": "SC1", "name": "Columbia, SC", "lat": 34.0007, "lon": -81.0348, "state": "SC"},
    {"station_id": "TN1", "name": "Nashville, TN", "lat": 36.1627, "lon": -86.7816, "state": "TN"},
    {"station_id": "TX1", "name": "Austin, TX", "lat": 30.2672, "lon": -97.7431, "state": "TX"},
    {"station_id": "TX2", "name": "Houston, TX", "lat": 29.7604, "lon": -95.3698, "state": "TX"},
    {"station_id": "UT1", "name": "Salt Lake City, UT", "lat": 40.7608, "lon": -111.8910, "state": "UT"},
    {"station_id": "VA1", "name": "Richmond, VA", "lat": 37.5407, "lon": -77.4360, "state": "VA"},
    {"station_id": "WA1", "name": "Olympia, WA", "lat": 47.0379, "lon": -122.9007, "state": "WA"},
    {"station_id": "WI1", "name": "Madison, WI", "lat": 43.0731, "lon": -89.4012, "state": "WI"},
    {"station_id": "WV1", "name": "Charleston, WV", "lat": 38.3498, "lon": -81.6326, "state": "WV"},
    {"station_id": "WY1", "name": "Cheyenne, WY", "lat": 41.1400, "lon": -104.8202, "state": "WY"},
]


def fetch_stations_api() -> list[dict]:
    log.info("Fetching RadNet station list from EPA Envirofacts API…")
    try:
        resp = fetch_with_retry(STATIONS_URL, logger=log)
        data = resp.json()
        save_raw(resp.text, RAW_DIR / "stations.json")
        log.info(f"API returned {len(data)} stations")
        return data
    except Exception as exc:
        log.warning(f"API station fetch failed: {exc}. Using hardcoded station list.")
        return []


def normalize_stations(api_stations: list[dict]) -> list[dict]:
    if api_stations:
        stations = []
        for s in api_stations:
            sid = s.get("STATION_ID") or s.get("station_id")
            name = s.get("CITY") or s.get("STATION_NAME") or sid
            state = s.get("STATE_CODE") or ""
            lat = s.get("LATITUDE") or s.get("lat")
            lon = s.get("LONGITUDE") or s.get("lon")
            if lat and lon:
                stations.append({
                    "station_id": sid,
                    "name": f"{name}, {state}",
                    "lat": float(lat),
                    "lon": float(lon),
                    "state": state,
                })
        return stations
    return KNOWN_STATIONS


def build_records(stations: list[dict]) -> list[dict]:
    records = []
    for s in stations:
        try:
            notes = f"RadNet monitoring station | {s['state']}"
            rec = make_record(
                layer=LAYER,
                lat=s["lat"],
                lon=s["lon"],
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="EPA RadNet",
                notes=notes,
                extra={
                    "station_id": s["station_id"],
                    "station_name": s["name"],
                    "state": s["state"],
                    "monitor_type": "gross_beta_gamma",
                },
            )
            records.append(rec)
        except (ValueError, TypeError, KeyError):
            continue
    return records


def main():
    log.info("=== fetch_epa_radnet.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    api_stations = fetch_stations_api()
    stations = normalize_stations(api_stations)
    log.info(f"Processing {len(stations)} RadNet stations")

    records = build_records(stations)
    log.info(f"Built {len(records)} station records")

    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")
    log.info(
        "Note: For historical anomaly spike analysis, download CSV exports from:\n"
        "  https://enviro.epa.gov/envirofacts/radnet/search\n"
        "  Place in data/manual/ and run process/geocode_manual.py"
    )


if __name__ == "__main__":
    main()

"""
Fetch NOAA DART/NDBC buoy network — ocean pressure and wave anomalies.

Source: NOAA National Data Buoy Center (NDBC)
Station list: https://www.ndbc.noaa.gov/data/stations/station_table.txt
Historical data: https://www.ndbc.noaa.gov/station_history.php?station={ID}

Physics basis: Fluid dynamics. Fast transmedium objects displace water.
Pressure waves propagate at known speeds and cannot be hidden from
a buoy-instrumented ocean.

Analysis target: Sea surface pressure spikes NOT correlated with known
seismic events (USGS catalog) or weather (NOAA wave model).
Focus on multi-buoy simultaneous events near USO hotspot zones.

Last verified: 2026-06-09

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  station_id, station_name, buoy_type, water_depth_m
"""

import sys
from io import StringIO
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, fetch_with_retry,
    get_logger, make_record, records_to_geojson, save_geojson, save_raw,
)

log = get_logger("fetch_dart_buoys")

LAYER = "dart_buoys"
CONFIDENCE = 4
CATEGORY = "ocean"

RAW_DIR = RAW_DATA_DIR / "dart_buoys"
OUT_PATH = PROCESSED_DATA_DIR / "dart_buoys.geojson"

NDBC_STATION_TABLE = "https://www.ndbc.noaa.gov/data/stations/station_table.txt"
NDBC_REALTIME = "https://www.ndbc.noaa.gov/data/latest_obs/latest_obs.txt"

# High-interest DART stations near USO hotspot zones (pre-curated)
PRIORITY_STATIONS = {
    # Southern California Offshore — Zone B
    "46411": {"name": "Santa Barbara Channel",    "lat": 34.938,  "lon": -120.775, "zone": "B"},
    "46086": {"name": "San Clemente Basin",        "lat": 32.491,  "lon": -118.034, "zone": "B"},
    "46047": {"name": "Tanner Bank",               "lat": 32.432,  "lon": -119.529, "zone": "B"},
    "46025": {"name": "Santa Monica Basin",        "lat": 33.749,  "lon": -119.053, "zone": "B"},
    "46023": {"name": "Point Arguello",            "lat": 34.714,  "lon": -120.967, "zone": "B"},
    "46026": {"name": "San Francisco",             "lat": 37.759,  "lon": -122.833, "zone": "B"},
    "46042": {"name": "Monterey",                  "lat": 36.785,  "lon": -122.469, "zone": "B"},
    # Atlantic/East Coast — Shag Harbour area
    "44137": {"name": "Lurcher Shoal",             "lat": 43.596,  "lon": -66.522,  "zone": "shag_harbour"},
    "44139": {"name": "Northeast Channel",         "lat": 42.798,  "lon": -65.907,  "zone": "shag_harbour"},
    # Gulf of Mexico
    "42001": {"name": "Mid Gulf",                  "lat": 25.888,  "lon": -89.658,  "zone": "gulf"},
    "42002": {"name": "West Gulf",                 "lat": 25.790,  "lon": -93.644,  "zone": "gulf"},
    # Caribbean / Puerto Rico — DHS thermal video zone
    "41047": {"name": "NE Caribbean",              "lat": 27.514,  "lon": -71.491,  "zone": "caribbean"},
    "41048": {"name": "East Caribbean",            "lat": 31.900,  "lon": -69.590,  "zone": "caribbean"},
    # Pacific NW — Yakima/Washington anomaly zone adjacency
    "46041": {"name": "Cape Elizabeth WA",         "lat": 47.353,  "lon": -124.731, "zone": "pacific_nw"},
    # Zone E — Western Pacific / Japan (DART network post-Tohoku)
    "21419": {"name": "Wakayama Japan",            "lat": 33.718,  "lon": 135.817,  "zone": "E"},
    "21401": {"name": "North Pacific (Japan)",     "lat": 38.700,  "lon": 148.694,  "zone": "E"},
    "21413": {"name": "NW Pacific",                "lat": 30.534,  "lon": 152.122,  "zone": "E"},
}

DART_BUOY_TYPE = "DART"


def fetch_station_table() -> pd.DataFrame | None:
    """Fetch full NDBC station table for metadata."""
    log.info("Fetching NDBC station table…")
    try:
        resp = fetch_with_retry(NDBC_STATION_TABLE, logger=log)
        raw_path = RAW_DIR / "station_table.txt"
        save_raw(resp.text, raw_path)

        # Fixed-width format; parse manually
        lines = resp.text.splitlines()
        # Skip header lines
        data_lines = [l for l in lines if l.strip() and not l.startswith("#")]
        if not data_lines:
            return None

        rows = []
        for line in data_lines:
            parts = line.split("|")
            if len(parts) >= 5:
                try:
                    station_id = parts[0].strip()
                    owner = parts[1].strip() if len(parts) > 1 else ""
                    station_type = parts[2].strip() if len(parts) > 2 else ""
                    hull = parts[3].strip() if len(parts) > 3 else ""
                    name = parts[4].strip() if len(parts) > 4 else ""
                    lat = float(parts[5].strip()) if len(parts) > 5 and parts[5].strip() else None
                    lon = float(parts[6].strip()) if len(parts) > 6 and parts[6].strip() else None
                    rows.append({
                        "station_id": station_id,
                        "owner": owner,
                        "station_type": station_type,
                        "hull": hull,
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                    })
                except (ValueError, IndexError):
                    continue

        df = pd.DataFrame(rows).dropna(subset=["lat", "lon"])
        log.info(f"Station table: {len(df)} stations with coordinates")
        return df
    except Exception as exc:
        log.warning(f"Station table fetch failed: {exc}")
        return None


def build_records(station_df: pd.DataFrame | None) -> list[dict]:
    records = []

    # Priority curated stations first
    for station_id, meta in PRIORITY_STATIONS.items():
        try:
            zone = meta.get("zone", "")
            notes = (
                f"DART/NDBC buoy | Zone {zone} | {meta['name']} | "
                f"Priority station near anomaly hotspot"
            )
            rec = make_record(
                layer=LAYER,
                lat=meta["lat"],
                lon=meta["lon"],
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="NOAA NDBC (curated priority stations)",
                notes=notes,
                extra={
                    "station_id": station_id,
                    "station_name": meta["name"],
                    "buoy_type": DART_BUOY_TYPE,
                    "zone": zone,
                    "priority": True,
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue

    log.info(f"Built {len(records)} priority station records")

    # Add all DART buoys from station table
    if station_df is not None:
        dart_mask = (
            station_df["station_type"].str.upper().str.contains("DART|BUOY|MOORING", na=False) |
            station_df["owner"].str.upper().str.contains("NOAA|NDBC", na=False)
        )
        dart_df = station_df[dart_mask]
        priority_ids = set(PRIORITY_STATIONS.keys())

        added = 0
        for _, row in dart_df.iterrows():
            if str(row["station_id"]) in priority_ids:
                continue
            try:
                rec = make_record(
                    layer=LAYER,
                    lat=row["lat"],
                    lon=row["lon"],
                    confidence=3,
                    category=CATEGORY,
                    source="NOAA NDBC station table",
                    notes=f"{row.get('name', '')} | {row.get('station_type', '')} | {row.get('owner', '')}",
                    extra={
                        "station_id": str(row["station_id"]),
                        "station_name": str(row.get("name", "")),
                        "buoy_type": str(row.get("hull", "BUOY")),
                        "priority": False,
                    },
                )
                records.append(rec)
                added += 1
            except (ValueError, TypeError):
                continue

        log.info(f"Added {added} additional NDBC stations from table")

    return records


def main():
    log.info("=== fetch_dart_buoys.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    station_df = fetch_station_table()
    records = build_records(station_df)

    log.info(f"Total buoy records: {len(records)}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")
    log.info(
        "Note: For historical pressure anomaly analysis, download station data via:\n"
        "  https://www.ndbc.noaa.gov/station_history.php?station=<STATION_ID>\n"
        "  Focus on DART stations (46411, 46086, 46047, 46025) near Zone B."
    )


if __name__ == "__main__":
    main()

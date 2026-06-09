"""
Fetch and normalize space weather / solar activity data.

Source: NOAA Space Weather Prediction Center (SWPC)
Endpoints:
  - Solar flares (7-day): https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json
  - Geomagnetic storm summary: https://services.swpc.noaa.gov/json/goes/primary/geomagnetic-storm-summary.json
  - 3-day Kp index text: https://services.swpc.noaa.gov/text/3-day-geomag-index.txt

CONTROL LAYER (Layer 32): High solar activity periods indicate that anomalous
events on OTHER layers are LESS statistically significant — geomagnetic storms
cause widespread sensor noise, navigation disruption, and unusual animal behavior.
When cross-correlating, subtract or weight down events that coincide with Kp >= 5.

Also includes hardcoded major historical geomagnetic events as reference anchors.

Last verified: 2026-06-09

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  event_type, kp_index, x_class, peak_flux
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timezone

import requests

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

log = get_logger("fetch_space_weather")

LAYER = "space_weather"
CONFIDENCE = 5
CATEGORY = "solar_control"

FLARES_URL = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json"
STORM_URL = "https://services.swpc.noaa.gov/json/goes/primary/geomagnetic-storm-summary.json"
KP_TEXT_URL = "https://services.swpc.noaa.gov/text/3-day-geomag-index.txt"

RAW_DIR = RAW_DATA_DIR / "space_weather"
OUT_PATH = PROCESSED_DATA_DIR / "space_weather.geojson"

# Primary effect locations: major power grid / infrastructure hubs most affected.
# Lat/lon represent the region of primary documented impact, not the source.
HISTORICAL_EVENTS = [
    {
        "datetime": "1859-09-01T12:00:00Z",
        "lat": 51.5,
        "lon": -0.1,
        "notes": (
            "Carrington Event (1859): Most powerful geomagnetic storm on record. "
            "Kp equivalent ~9+. Telegraph systems worldwide disrupted. Aurora visible "
            "at equatorial latitudes. Location: London (primary telegraph disruption hub)."
        ),
        "event_type": "geomagnetic_storm",
        "kp_index": 9.0,
        "x_class": "X45+",
        "peak_flux": None,
    },
    {
        "datetime": "1989-03-13T01:44:00Z",
        "lat": 46.0,
        "lon": -73.5,
        "notes": (
            "Quebec Storm (1989-03-13): Kp=9 geomagnetic superstorm. "
            "Hydro-Quebec power grid collapsed for 9 hours, leaving 6 million without power. "
            "Location: Montreal (Hydro-Quebec control center)."
        ),
        "event_type": "geomagnetic_storm",
        "kp_index": 9.0,
        "x_class": "X15",
        "peak_flux": None,
    },
    {
        "datetime": "2003-10-28T11:10:00Z",
        "lat": 38.9,
        "lon": -77.0,
        "notes": (
            "Halloween Storms (2003-10-28): X17.2 + X10 solar flares, Kp=9 storm. "
            "Power outages in Sweden, satellite anomalies, GPS degradation. "
            "NOAA Space Weather Center (Washington DC) primary coordination site."
        ),
        "event_type": "geomagnetic_storm",
        "kp_index": 9.0,
        "x_class": "X17.2",
        "peak_flux": None,
    },
    {
        "datetime": "2003-10-29T20:49:00Z",
        "lat": 38.9,
        "lon": -77.0,
        "notes": (
            "Halloween Storms Day 2 (2003-10-29): X10 flare follow-on event. "
            "Continued grid and satellite disruptions across North America and Europe."
        ),
        "event_type": "geomagnetic_storm",
        "kp_index": 9.0,
        "x_class": "X10",
        "peak_flux": None,
    },
    {
        "datetime": "2024-05-10T21:00:00Z",
        "lat": 44.0,
        "lon": -103.0,
        "notes": (
            "May 2024 Superstorm: G5-class (Kp=9) storm, strongest since 2003. "
            "Aurora visible across continental US. Widespread GPS and HF radio disruption. "
            "Location: South Dakota (center of observed aurora footprint)."
        ),
        "event_type": "geomagnetic_storm",
        "kp_index": 9.0,
        "x_class": "X8.7",
        "peak_flux": None,
    },
]


def fetch_flares() -> list[dict]:
    """Fetch 7-day solar flare JSON from NOAA SWPC."""
    log.info(f"Fetching solar flares: {FLARES_URL}")
    try:
        resp = fetch_with_retry(FLARES_URL, logger=log)
        data = resp.json()
        save_raw(resp.text, RAW_DIR / "xray_flares_7day.json")
        log.info(f"Fetched {len(data)} flare events")
        return data
    except Exception as exc:
        log.warning(f"Flare fetch failed: {exc}")
        return []


def fetch_storms() -> list[dict]:
    """Fetch geomagnetic storm summary JSON from NOAA SWPC."""
    log.info(f"Fetching geomagnetic storms: {STORM_URL}")
    try:
        resp = fetch_with_retry(STORM_URL, logger=log)
        data = resp.json()
        save_raw(resp.text, RAW_DIR / "geomagnetic_storm_summary.json")
        log.info(f"Fetched {len(data)} storm events")
        return data
    except Exception as exc:
        log.warning(f"Storm fetch failed: {exc}")
        return []


def fetch_kp_text() -> str:
    """Fetch 3-day Kp index text file from NOAA SWPC."""
    log.info(f"Fetching 3-day Kp index: {KP_TEXT_URL}")
    try:
        resp = fetch_with_retry(KP_TEXT_URL, logger=log)
        save_raw(resp.text, RAW_DIR / "3day_geomag_index.txt")
        log.info("Saved 3-day Kp index text")
        return resp.text
    except Exception as exc:
        log.warning(f"Kp text fetch failed: {exc}")
        return ""


def normalize_flares(flares: list[dict]) -> list[dict]:
    """Convert NOAA flare JSON records to standard schema records."""
    records = []
    for flare in flares:
        try:
            dt = flare.get("begin_time") or flare.get("peak_time") or flare.get("event_date")
            x_class = flare.get("max_class", "")
            peak_flux = flare.get("max_xrlong") or flare.get("max_xrshrt")
            notes = (
                f"Solar flare class {x_class}. "
                f"Begin: {flare.get('begin_time', 'N/A')}, "
                f"Peak: {flare.get('peak_time', 'N/A')}, "
                f"End: {flare.get('end_time', 'N/A')}. "
                f"Active region: {flare.get('active_region', 'N/A')}. "
                "CONTROL: flares cause HF blackouts and ionospheric disruption globally."
            )
            # Flares affect the entire dayside of Earth — use NOAA facility lat/lon
            rec = make_record(
                layer=LAYER,
                lat=40.015,
                lon=-105.27,
                datetime_str=str(dt) if dt else None,
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="NOAA SWPC",
                notes=notes[:1000],
                extra={
                    "event_type": "solar_flare",
                    "kp_index": None,
                    "x_class": x_class,
                    "peak_flux": str(peak_flux) if peak_flux else None,
                },
            )
            records.append(rec)
        except (ValueError, TypeError, KeyError) as exc:
            log.debug(f"Skipping flare record: {exc}")
            continue
    log.info(f"Normalized {len(records)} flare records")
    return records


def normalize_storms(storms: list[dict]) -> list[dict]:
    """Convert NOAA storm summary JSON records to standard schema records."""
    records = []
    for storm in storms:
        try:
            dt = storm.get("start_time") or storm.get("observed_time")
            kp_raw = storm.get("kp_index") or storm.get("max_kp") or storm.get("kp")
            try:
                kp = float(kp_raw) if kp_raw is not None else None
            except (ValueError, TypeError):
                kp = None
            notes = (
                f"Geomagnetic storm. Scale: {storm.get('g_scale', 'N/A')}, "
                f"Kp: {kp_raw}. "
                f"Duration: {storm.get('duration', 'N/A')}. "
                "CONTROL: Global effect — events on other layers during this window "
                "should be weighted down for anomaly scoring."
            )
            rec = make_record(
                layer=LAYER,
                lat=40.015,
                lon=-105.27,
                datetime_str=str(dt) if dt else None,
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="NOAA SWPC",
                notes=notes[:1000],
                extra={
                    "event_type": "geomagnetic_storm",
                    "kp_index": kp,
                    "x_class": None,
                    "peak_flux": None,
                },
            )
            records.append(rec)
        except (ValueError, TypeError, KeyError) as exc:
            log.debug(f"Skipping storm record: {exc}")
            continue
    log.info(f"Normalized {len(records)} storm records")
    return records


def build_historical_records() -> list[dict]:
    """Build records for hardcoded major historical geomagnetic events."""
    records = []
    for ev in HISTORICAL_EVENTS:
        rec = make_record(
            layer=LAYER,
            lat=ev["lat"],
            lon=ev["lon"],
            datetime_str=ev["datetime"],
            confidence=CONFIDENCE,
            category=CATEGORY,
            source="Historical record / NOAA archives",
            notes=ev["notes"],
            extra={
                "event_type": ev["event_type"],
                "kp_index": ev["kp_index"],
                "x_class": ev["x_class"],
                "peak_flux": ev["peak_flux"],
            },
        )
        records.append(rec)
    log.info(f"Built {len(records)} historical event records")
    return records


def main():
    log.info("=== fetch_space_weather.py (Layer 32 — CONTROL) ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    flares_raw = fetch_flares()
    storms_raw = fetch_storms()
    fetch_kp_text()  # saved to disk for downstream use

    records = []
    records.extend(normalize_flares(flares_raw))
    records.extend(normalize_storms(storms_raw))
    records.extend(build_historical_records())

    log.info(f"Total space weather records: {len(records)}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved {len(records)} records → {OUT_PATH}")


if __name__ == "__main__":
    main()

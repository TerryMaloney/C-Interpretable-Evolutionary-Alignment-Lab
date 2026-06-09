"""
Build nuclear and classified research facility location dataset.

Sources:
  - NRC Reactor list: https://www.nrc.gov/info-finder/reactor/
  - DOE National Labs: https://www.energy.gov/national-labs
  - Manually curated list of high-interest sites with documented UAP incidents

This script combines:
1. Known high-interest sites (hardcoded with full documentation)
2. NRC commercial reactor list (fetched from NRC website)

Last verified: 2026-06-09

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  facility_name, facility_type, operator, uap_incidents_documented
"""

import sys
from pathlib import Path

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

log = get_logger("fetch_nuclear_facilities")

LAYER = "nuclear_facilities"
CONFIDENCE = 5
CATEGORY = "infrastructure"

RAW_DIR = RAW_DATA_DIR / "nuclear_facilities"
OUT_PATH = PROCESSED_DATA_DIR / "nuclear_facilities.geojson"

# Curated high-interest sites with documented UAP/anomalous incident history
HIGH_INTEREST_SITES = [
    {
        "name": "Hanford Site",
        "lat": 46.5505, "lon": -119.4888,
        "state": "WA",
        "type": "doe_weapons",
        "operator": "DOE",
        "uap_documented": True,
        "notes": (
            "Pre-Roswell UAP wave over nuclear production site 1946-47. "
            "First major US plutonium production facility. "
            "Multiple documented radar and visual UAP incidents."
        ),
    },
    {
        "name": "Los Alamos National Laboratory",
        "lat": 35.8811, "lon": -106.3031,
        "state": "NM",
        "type": "doe_lab",
        "operator": "DOE/NNSA",
        "uap_documented": True,
        "notes": (
            "Manhattan Project birthplace. Multiple green fireball waves 1948-51. "
            "Dr. Lincoln LaPaz USAF investigation documented. "
            "Rio Grande Rift underlies site."
        ),
    },
    {
        "name": "Sandia National Laboratories",
        "lat": 35.0544, "lon": -106.5488,
        "state": "NM",
        "type": "doe_lab",
        "operator": "DOE/NNSA",
        "uap_documented": True,
        "notes": (
            "Nuclear weapons engineering facility. Kirtland AFB co-location. "
            "Multiple classified UAP incidents per FOIA documents. "
            "Adjacent Kirtland Underground Munitions Storage Complex (KUMSC)."
        ),
    },
    {
        "name": "Savannah River Site",
        "lat": 33.3469, "lon": -81.7284,
        "state": "SC",
        "type": "doe_weapons",
        "operator": "DOE",
        "uap_documented": True,
        "notes": (
            "Tritium production facility. South Carolina most seismically active "
            "East Coast state. Multiple UAP reports from facility workers."
        ),
    },
    {
        "name": "Lawrence Livermore National Laboratory",
        "lat": 37.6879, "lon": -121.7063,
        "state": "CA",
        "type": "doe_lab",
        "operator": "DOE/NNSA",
        "uap_documented": False,
        "notes": "Nuclear weapons design lab. Bay Area seismically active zone.",
    },
    {
        "name": "Malmstrom Air Force Base",
        "lat": 47.5105, "lon": -111.1858,
        "state": "MT",
        "type": "military_icbm",
        "operator": "USAF",
        "uap_documented": True,
        "notes": (
            "March 1967: UAP hovered over missile field; 10 Minuteman ICBMs "
            "simultaneously went to 'No-Go' status. Captain Robert Salas eyewitness. "
            "Most documented nuclear-UAP incident on record."
        ),
    },
    {
        "name": "Nevada Test Site (Nevada National Security Site)",
        "lat": 37.1000, "lon": -116.0500,
        "state": "NV",
        "type": "doe_weapons",
        "operator": "DOE/NNSA",
        "uap_documented": True,
        "notes": (
            "928 nuclear weapons tests 1951-1992. Proximity to Area 51 (60 miles). "
            "Multiple UAP reports over test ranges. "
            "Extensive post-test atmospheric monitoring."
        ),
    },
    {
        "name": "Dugway Proving Ground",
        "lat": 40.1939, "lon": -113.0591,
        "state": "UT",
        "type": "military_test",
        "operator": "US Army",
        "uap_documented": True,
        "notes": (
            "Chemical/biological weapons testing. 85 miles SW Salt Lake City. "
            "Uintah Basin (Skinwalker Ranch) 100 miles NE. "
            "Restricted airspace; high UAP density in surrounding region."
        ),
    },
    {
        "name": "Skinwalker Ranch (AAWSAP Research Site)",
        "lat": 40.2572, "lon": -109.8910,
        "state": "UT",
        "type": "government_research",
        "operator": "DIA (formerly)",
        "uap_documented": True,
        "notes": (
            "DIA AAWSAP $22M contract 2008. 38 classified technical reports. "
            "Documented radiation anomalies, animal injuries, instrument failures. "
            "Uintah Basin; active seismic zone; Uinta Mountains fault system."
        ),
    },
    {
        "name": "Area 51 / Groom Lake",
        "lat": 37.2350, "lon": -115.8111,
        "state": "NV",
        "type": "military_classified",
        "operator": "USAF/CIA",
        "uap_documented": True,
        "notes": (
            "Officially acknowledged 2013. Advanced aircraft testing (U-2, SR-71, F-117). "
            "Proximate to Nevada Test Site. "
            "Many 'UAP' sightings likely classified aircraft tests."
        ),
    },
    {
        "name": "White Sands Missile Range",
        "lat": 32.3838, "lon": -106.4826,
        "state": "NM",
        "type": "military_test",
        "operator": "US Army",
        "uap_documented": True,
        "notes": (
            "First atomic bomb test (Trinity Site, 1945). Ongoing classified testing. "
            "Adjacent to Holloman AFB. Green fireball incidents 1948-51. "
            "Rio Grande Rift proximity."
        ),
    },
    {
        "name": "China Lake Naval Air Weapons Station",
        "lat": 35.6841, "lon": -117.6853,
        "state": "CA",
        "type": "military_test",
        "operator": "US Navy",
        "uap_documented": False,
        "notes": "Largest Navy land holding. Massive restricted airspace. Mojave Desert seismics.",
    },
    {
        "name": "Raven Rock Mountain Complex (Site R)",
        "lat": 39.7186, "lon": -77.4636,
        "state": "PA",
        "type": "dumb",
        "operator": "DoD",
        "uap_documented": False,
        "notes": "Alternate Pentagon; confirmed deep underground facility. Blue Ridge Mountains granite.",
    },
    {
        "name": "Mount Weather Emergency Operations Center",
        "lat": 39.0639, "lon": -77.8878,
        "state": "VA",
        "type": "dumb",
        "operator": "FEMA/DHS",
        "uap_documented": False,
        "notes": "Confirmed underground continuity facility. Blue Ridge Mountains quartzite.",
    },
    {
        "name": "Cheyenne Mountain Complex",
        "lat": 38.7442, "lon": -104.8460,
        "state": "CO",
        "type": "dumb",
        "operator": "NORAD/USSPACECOM",
        "uap_documented": True,
        "notes": "NORAD headquarters. 1,800ft granite mountain. Multiple UAP tracked entries/exits.",
    },
    {
        "name": "Skunk Works Plant 42 (Palmdale)",
        "lat": 34.6291, "lon": -118.0839,
        "state": "CA",
        "type": "defense_contractor",
        "operator": "Lockheed Martin",
        "uap_documented": False,
        "notes": "Advanced aircraft manufacturing. Antelope Valley black project corridor.",
    },
    {
        "name": "Helendale RCS Test Facility",
        "lat": 34.7366, "lon": -117.3161,
        "state": "CA",
        "type": "defense_contractor",
        "operator": "Lockheed Martin",
        "uap_documented": False,
        "notes": "Radar cross-section testing. Visible on satellite imagery.",
    },
]

# NRC reactor list URL (public)
NRC_REACTOR_URL = "https://www.nrc.gov/reactors/operating/list-power-reactor-units.html"


def fetch_nrc_reactors() -> list[dict]:
    """Fetch NRC commercial reactor list. Returns list of facility dicts."""
    log.info("Fetching NRC reactor list…")
    try:
        import re
        resp = fetch_with_retry(NRC_REACTOR_URL, logger=log)
        save_raw(resp.text, RAW_DIR / "nrc_reactors.html")

        # Parse HTML table — NRC page has a table with Name, Location, State, etc.
        # Use pandas to parse HTML tables
        import pandas as pd
        from io import StringIO
        tables = pd.read_html(StringIO(resp.text))
        if not tables:
            log.warning("No tables found in NRC page")
            return []

        df = tables[0]
        df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]
        log.info(f"NRC table columns: {list(df.columns)}")
        log.info(f"NRC reactors: {len(df)}")
        return df.to_dict("records")
    except Exception as exc:
        log.warning(f"NRC reactor fetch failed: {exc}")
        return []


def geocode_nrc_reactors(reactors: list[dict]) -> list[dict]:
    """
    Geocode NRC reactors by city/state using Nominatim.
    NRC list doesn't include coordinates — geocoding to city level.
    """
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut
        import time
    except ImportError:
        log.warning("geopy not installed; skipping NRC reactor geocoding")
        return []

    geocoder = Nominatim(user_agent="anomaly_map_project/1.0")
    records = []

    for reactor in reactors:
        try:
            # Try to find location fields
            name = reactor.get("plant_name") or reactor.get("name") or str(reactor)
            state = reactor.get("state") or ""
            city = reactor.get("city") or reactor.get("location") or ""
            status = reactor.get("status") or reactor.get("operational_status") or "Unknown"

            query = f"{city}, {state}, USA" if city else f"{state}, USA"
            try:
                location = geocoder.geocode(query, timeout=10)
                time.sleep(1.1)  # Nominatim rate limit: 1 req/sec
            except GeocoderTimedOut:
                location = None

            if not location:
                continue

            rec = make_record(
                layer=LAYER,
                lat=location.latitude,
                lon=location.longitude,
                confidence=4,
                category=CATEGORY,
                source="NRC Operating Reactor List",
                notes=f"{name} | {status} | {state}",
                extra={
                    "facility_name": name,
                    "facility_type": "commercial_reactor",
                    "operator": "Commercial",
                    "state": state,
                    "status": status,
                    "uap_incidents_documented": False,
                },
            )
            records.append(rec)
        except Exception:
            continue

    log.info(f"Geocoded {len(records)} NRC reactors")
    return records


def build_curated_records() -> list[dict]:
    records = []
    for site in HIGH_INTEREST_SITES:
        try:
            rec = make_record(
                layer=LAYER,
                lat=site["lat"],
                lon=site["lon"],
                confidence=5 if site["uap_documented"] else 4,
                category=CATEGORY,
                source="Curated — FOIA/Congressional/Public record",
                notes=site["notes"],
                extra={
                    "facility_name": site["name"],
                    "facility_type": site["type"],
                    "operator": site["operator"],
                    "state": site["state"],
                    "uap_incidents_documented": site["uap_documented"],
                },
            )
            records.append(rec)
        except (ValueError, TypeError) as exc:
            log.warning(f"Skipping {site['name']}: {exc}")
    log.info(f"Built {len(records)} curated facility records")
    return records


def main():
    log.info("=== fetch_nuclear_facilities.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Build curated list
    records = build_curated_records()

    # Add NRC commercial reactors
    nrc_reactors = fetch_nrc_reactors()
    if nrc_reactors:
        nrc_records = geocode_nrc_reactors(nrc_reactors)
        records.extend(nrc_records)

    log.info(f"Total facility records: {len(records)}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()

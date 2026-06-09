"""
Fetch NOAA Marine Mammal Unusual Mortality Events (UME) stranding locations.

Source: NOAA Fisheries Marine Mammal Health and Stranding Response Program
ArcGIS Feature Services:
  - Right Whale UME: https://services2.arcgis.com/C8EMgrsFcRFL6LrL/arcgis/rest/services/
      Right_Whale_UME_Stranding_Locations_View/FeatureServer/0/query
  - NOAA UME list: https://www.fisheries.noaa.gov/national/marine-life-distress/
      active-and-closed-unusual-mortality-events

Last verified: 2026-06-09

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  species, event_type, cause_determination
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

log = get_logger("fetch_noaa_ume")

LAYER = "noaa_ume"
CONFIDENCE = 5
CATEGORY = "marine"

RAW_DIR = RAW_DATA_DIR / "noaa_ume"
OUT_PATH = PROCESSED_DATA_DIR / "noaa_ume.geojson"

ARCGIS_ENDPOINTS = [
    {
        "name": "Right Whale UME 2017-present",
        "url": (
            "https://services2.arcgis.com/C8EMgrsFcRFL6LrL/arcgis/rest/services/"
            "Right_Whale_UME_Stranding_Locations_View/FeatureServer/0/query"
        ),
        "species": "North Atlantic Right Whale",
    },
    {
        "name": "Humpback Whale UME 2016-2024",
        "url": (
            "https://services2.arcgis.com/C8EMgrsFcRFL6LrL/arcgis/rest/services/"
            "Humpback_Whale_UME_2016_2024/FeatureServer/0/query"
        ),
        "species": "Humpback Whale",
    },
    {
        "name": "Gray Whale UME",
        "url": (
            "https://services2.arcgis.com/C8EMgrsFcRFL6LrL/arcgis/rest/services/"
            "Gray_Whale_UME_Strandings/FeatureServer/0/query"
        ),
        "species": "Gray Whale",
    },
]

ARCGIS_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "f": "geojson",
    "resultRecordCount": 5000,
}


def fetch_endpoint(endpoint: dict) -> list[dict]:
    name = endpoint["name"]
    url = endpoint["url"]
    log.info(f"Fetching {name}…")
    try:
        resp = fetch_with_retry(url, params=ARCGIS_PARAMS, logger=log)
        data = resp.json()
        features = data.get("features", [])
        raw_path = RAW_DIR / f"{name.lower().replace(' ', '_')}.geojson"
        save_raw(resp.text, raw_path)
        log.info(f"  {name}: {len(features)} features")
        return features
    except Exception as exc:
        log.warning(f"  {name} failed: {exc}")
        return []


def normalize(features: list[dict], default_species: str) -> list[dict]:
    records = []
    for feat in features:
        geom = feat.get("geometry", {})
        if not geom or geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]

        props = feat.get("properties", {}) or {}
        species = (
            props.get("CommonName")
            or props.get("species")
            or props.get("SPECIES")
            or default_species
        )
        event_date = (
            props.get("EventDate")
            or props.get("event_date")
            or props.get("OBSERVATION_DATE")
            or props.get("Date")
        )
        stranding_type = props.get("StrandingType") or props.get("stranding_type") or ""
        cause = props.get("CauseDetermination") or props.get("cause_determination") or "Unknown"
        state = props.get("State") or props.get("state") or ""

        if isinstance(event_date, (int, float)):
            from datetime import datetime, timezone
            try:
                event_date = datetime.fromtimestamp(event_date / 1000, tz=timezone.utc).isoformat()
            except Exception:
                event_date = str(event_date)

        notes = f"{species} | {stranding_type} | Cause: {cause}"
        if state:
            notes += f" | {state}"

        try:
            rec = make_record(
                layer=LAYER,
                lat=lat,
                lon=lon,
                datetime_str=str(event_date) if event_date else None,
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="NOAA MMHSRP ArcGIS",
                notes=notes,
                extra={
                    "species": species,
                    "stranding_type": stranding_type,
                    "cause_determination": cause,
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue
    return records


def main():
    log.info("=== fetch_noaa_ume.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_records = []
    for endpoint in ARCGIS_ENDPOINTS:
        features = fetch_endpoint(endpoint)
        records = normalize(features, endpoint["species"])
        all_records.extend(records)

    log.info(f"Total UME records: {len(all_records):,}")
    gj = records_to_geojson(all_records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()

"""
Fetch FAA Special Use Airspace (SUA) polygons for military activity masking.

Source: FAA ArcGIS Open Data
https://adds-faa.opendata.arcgis.com/datasets/
Dataset: "Special Use Airspace"

Purpose: EXCLUSION MASK
  UAP clusters that fall entirely within Restricted/Prohibited airspace may be
  classified testing rather than anomalous phenomenon. These polygons let us
  flag co-located clusters as "may be classified testing" rather than signal.

Airspace types:
  R (Restricted):   Military operations; flight restricted without permission
  P (Prohibited):   No flight ever (nuclear plants, Camp David, etc.)
  W (Warning):      Hazardous activity; caution advised
  MOA (Military):   Military training; may have civilian traffic
  A (Alert):        High volume military activity

Analysis use:
  - Cross-reference UAP clusters: if centroid inside SUA polygon, flag as
    "possible classified testing" — do not discard, but lower signal weight
  - Nuclear facility UAP incidents near military restricted zones = lower value signal
  - UAP incidents IN non-SUA zones, away from military activity = higher value signal

Last verified: 2026-06-09

Output: GeoJSON with SUA polygon centroids (simplified for point map)
        Full polygons preserved as separate file for spatial join analysis
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, fetch_with_retry,
    get_logger, make_record, records_to_geojson, save_geojson, save_raw,
)

log = get_logger("fetch_faa_airspace")

LAYER = "faa_airspace"
CONFIDENCE = 5
CATEGORY = "mask"

RAW_DIR = RAW_DATA_DIR / "faa_airspace"
OUT_PATH = PROCESSED_DATA_DIR / "faa_airspace.geojson"
POLYGON_OUT_PATH = PROCESSED_DATA_DIR / "faa_airspace_polygons.geojson"

# FAA SUA ArcGIS Feature Service
FAA_SUA_URL = (
    "https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/arcgis/rest/services/"
    "Special_Use_Airspace/FeatureServer/0/query"
)
FAA_SUA_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "f": "geojson",
    "resultRecordCount": 5000,
}

# Type classification for mask scoring
HIGH_INTEREST_TYPES = {"R", "P"}  # Restricted + Prohibited
MEDIUM_INTEREST_TYPES = {"W", "MOA", "A"}

# Key large military restricted zones (manual fallback if API unavailable)
KEY_SUA_ZONES = [
    {"name": "Area 51 Restricted Airspace (R-4808)", "lat": 37.235, "lon": -115.811,
     "type": "R", "notes": "Groom Lake / Area 51 primary restricted zone"},
    {"name": "Nevada Test Site Restricted (R-4809)", "lat": 37.100, "lon": -116.050,
     "type": "R", "notes": "Nevada National Security Site nuclear test range"},
    {"name": "China Lake NAWS Restricted (R-2508)", "lat": 35.684, "lon": -117.685,
     "type": "R", "notes": "Largest US Navy restricted airspace — Mojave Desert"},
    {"name": "White Sands Restricted (R-5107)", "lat": 32.384, "lon": -106.483,
     "type": "R", "notes": "White Sands Missile Range restricted airspace"},
    {"name": "Edwards AFB Restricted (R-2515)", "lat": 34.905, "lon": -117.884,
     "type": "R", "notes": "Edwards AFB test range — stealth aircraft testing"},
    {"name": "Nellis AFB Restricted Complex (R-4806)", "lat": 37.25, "lon": -115.5,
     "type": "R", "notes": "Nellis AFB / Red Flag exercise area. Largest US restricted complex."},
    {"name": "Dugway Proving Ground (R-6403)", "lat": 40.194, "lon": -113.059,
     "type": "R", "notes": "Chemical/biological weapons test range"},
    {"name": "Camp David Prohibited (P-40)", "lat": 39.648, "lon": -77.462,
     "type": "P", "notes": "Presidential retreat — permanent prohibited airspace"},
    {"name": "Washington DC ADIZ (P-56)", "lat": 38.889, "lon": -77.009,
     "type": "P", "notes": "National Capital Region prohibited airspace"},
    {"name": "Point Mugu NAS (R-2501)", "lat": 34.117, "lon": -119.117,
     "type": "R", "notes": "Naval Air Weapons Station — missile testing Pacific"},
    {"name": "Vandenberg SFB (R-2527)", "lat": 34.726, "lon": -120.574,
     "type": "R", "notes": "Space launch and ICBM testing — Zone B adjacency"},
    {"name": "Yuma Proving Ground (R-2301)", "lat": 32.499, "lon": -114.390,
     "type": "R", "notes": "Army weapons testing — Arizona desert"},
    {"name": "Fort Bragg MOA", "lat": 35.139, "lon": -79.006,
     "type": "MOA", "notes": "82nd Airborne Division training area — East Coast"},
    {"name": "Melrose Range MOA (New Mexico)", "lat": 34.4, "lon": -104.1,
     "type": "MOA", "notes": "New Mexico air-to-ground weapons range — Zone A adjacency"},
]


def fetch_sua_api() -> list[dict]:
    """Fetch SUA polygons from FAA ArcGIS API."""
    log.info("Fetching FAA Special Use Airspace from ArcGIS API…")
    try:
        resp = fetch_with_retry(FAA_SUA_URL, params=FAA_SUA_PARAMS, logger=log)
        data = resp.json()
        features = data.get("features", [])
        save_raw(resp.text, RAW_DIR / "faa_sua.geojson")
        log.info(f"  FAA SUA API: {len(features)} features")
        return features
    except Exception as exc:
        log.warning(f"  FAA ArcGIS API failed: {exc}")
        return []


def process_api_features(features: list[dict]) -> tuple[list[dict], dict]:
    """Extract centroids from SUA polygons for point map, preserve full polygons."""
    try:
        from shapely.geometry import shape, mapping
    except ImportError:
        log.warning("shapely not available for polygon processing")
        return [], {}

    point_records = []
    polygon_features = []

    for feat in features:
        props = feat.get("properties", {}) or {}
        geom = feat.get("geometry", {})
        sua_type = props.get("TYPE_CODE") or props.get("AIRSPACE_TYPE") or ""
        name = props.get("NAME") or props.get("AIRSPACE_NAME") or ""
        lower_alt = props.get("LOWER_VAL") or ""
        upper_alt = props.get("UPPER_VAL") or ""

        # Preserve polygon
        polygon_features.append(feat)

        # Extract centroid
        try:
            geom_shape = shape(geom)
            centroid = geom_shape.centroid
            lat, lon = centroid.y, centroid.x

            is_high_interest = sua_type.upper() in HIGH_INTEREST_TYPES
            notes = (
                f"FAA {sua_type} airspace | {name} | "
                f"Alt: {lower_alt}-{upper_alt} | "
                f"{'HIGH INTEREST — military restricted' if is_high_interest else 'Military operational area'}"
            )

            rec = make_record(
                layer=LAYER,
                lat=lat,
                lon=lon,
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="FAA Special Use Airspace ArcGIS",
                notes=notes,
                extra={
                    "sua_type": sua_type,
                    "airspace_name": name,
                    "lower_alt": str(lower_alt),
                    "upper_alt": str(upper_alt),
                    "is_restricted": is_high_interest,
                    "mask_function": "Clusters inside may be classified testing",
                },
            )
            point_records.append(rec)
        except Exception:
            continue

    polygon_collection = {
        "type": "FeatureCollection",
        "features": polygon_features,
        "metadata": {"total_polygons": len(polygon_features)},
    }

    return point_records, polygon_collection


def build_manual_records() -> list[dict]:
    """Build records from hardcoded key SUA zones."""
    records = []
    for zone in KEY_SUA_ZONES:
        try:
            is_restricted = zone["type"] in HIGH_INTEREST_TYPES
            rec = make_record(
                layer=LAYER,
                lat=zone["lat"],
                lon=zone["lon"],
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="FAA SUA / Public record",
                notes=f"FAA {zone['type']} | {zone['name']} | {zone['notes']}",
                extra={
                    "sua_type": zone["type"],
                    "airspace_name": zone["name"],
                    "is_restricted": is_restricted,
                    "mask_function": "Clusters inside may be classified testing",
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue
    return records


def main():
    log.info("=== fetch_faa_airspace.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    api_features = fetch_sua_api()
    all_records = []
    polygon_collection = None

    if api_features:
        point_records, polygon_collection = process_api_features(api_features)
        all_records.extend(point_records)
        if polygon_collection:
            save_geojson(polygon_collection, POLYGON_OUT_PATH)
            log.info(f"Polygon data → {POLYGON_OUT_PATH}")
    else:
        log.info("Using manual key SUA zones as fallback")

    # Always include curated key zones
    manual_records = build_manual_records()
    all_records.extend(manual_records)

    # Deduplicate by proximity
    log.info(f"Total SUA point records: {len(all_records)}")
    gj = records_to_geojson(all_records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")
    log.info(
        f"\nSUA polygon file (for spatial join): {POLYGON_OUT_PATH}\n"
        "  Use with geopandas for: gdf.sjoin(sua_polygons) to flag\n"
        "  UAP clusters that fall inside restricted airspace."
    )


if __name__ == "__main__":
    main()

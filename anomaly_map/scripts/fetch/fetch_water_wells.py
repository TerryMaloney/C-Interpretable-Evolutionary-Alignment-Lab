"""
Fetch USGS NWIS groundwater level monitoring wells.

Source: USGS National Water Information System
API: https://waterservices.usgs.gov/nwis/gwlevels/
Library: dataretrieval (pip install dataretrieval)

Underground water movement — aquifer pressure changes, subsurface fluid
migration — precedes earthquakes and indicates subsurface structural changes.
Anomalous well level changes in non-drought, non-pumping conditions are signal.
The San Luis Valley aquifer is one of the largest in the US and sits in Zone A.

Last verified: 2026-06-09
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, fetch_with_retry,
    get_logger, make_record, records_to_geojson, save_geojson, save_raw,
)

log = get_logger("fetch_water_wells")

LAYER = "water_wells"
CONFIDENCE = 4
CATEGORY = "subsurface"

RAW_DIR = RAW_DATA_DIR / "water_wells"
OUT_PATH = PROCESSED_DATA_DIR / "water_wells.geojson"

NWIS_SITE_URL = "https://waterservices.usgs.gov/nwis/site/"
NWIS_GW_URL = "https://waterservices.usgs.gov/nwis/gwlevels/"

TARGET_STATES = ["CO", "NM", "UT", "CA", "NV"]

KNOWN_ANOMALOUS_AQUIFERS = [
    {"name": "San Luis Valley Unconfined Aquifer", "lat": 37.5, "lon": -106.0,
     "notes": "One of largest aquifers in US. Zone A center. Documented pressure anomalies preceding seismic events. Artesian conditions."},
    {"name": "Uintah Basin Aquifer System", "lat": 40.2, "lon": -109.8,
     "notes": "Uintah Basin groundwater. Skinwalker Ranch proximity. Oil/gas extraction disrupts water table. Documented anomalous pressure events."},
    {"name": "Española Basin Aquifer", "lat": 35.9, "lon": -106.1,
     "notes": "Rio Grande Rift basin aquifer. Los Alamos NL proximity. Fault-controlled groundwater movement."},
    {"name": "Tularosa Basin (White Sands)", "lat": 32.8, "lon": -106.2,
     "notes": "Closed basin. White Sands Missile Range underlies. Gypsum karst. Documented anomalous water level events."},
    {"name": "Owens Valley Aquifer", "lat": 36.5, "lon": -118.1,
     "notes": "Eastern Sierra Nevada. Zone B inland proximity. Sierra Nevada fault zone controls recharge."},
    {"name": "Imperial Valley Aquifer", "lat": 33.1, "lon": -115.5,
     "notes": "Salton Sea trough. Geothermal anomaly zone. Documented water level anomalies preceding Brawley seismic swarms."},
]


def fetch_gw_sites(state: str) -> list[dict]:
    params = {
        "stateCd": state,
        "siteType": "GW",
        "siteStatus": "active",
        "format": "rdb",
        "seriesCatalogOutput": "true",
    }
    log.info(f"Fetching groundwater sites for {state}…")
    try:
        resp = fetch_with_retry(NWIS_SITE_URL, params=params, logger=log)
        save_raw(resp.text, RAW_DIR / f"gw_sites_{state}.txt")

        sites = []
        for line in resp.text.splitlines():
            if line.startswith("#") or line.startswith("agency_cd"):
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            try:
                site_no = parts[1].strip()
                site_name = parts[2].strip()
                lat = float(parts[4].strip())
                lon = float(parts[5].strip())
                sites.append({"site_no": site_no, "name": site_name, "lat": lat, "lon": lon, "state": state})
            except (ValueError, IndexError):
                continue

        log.info(f"  {state}: {len(sites)} GW sites")
        return sites
    except Exception as exc:
        log.warning(f"  {state} site fetch failed: {exc}")
        return []


def normalize_sites(sites: list[dict]) -> list[dict]:
    records = []
    for s in sites:
        try:
            rec = make_record(
                layer=LAYER, lat=s["lat"], lon=s["lon"],
                confidence=CONFIDENCE, category=CATEGORY,
                source="USGS NWIS groundwater monitoring",
                notes=f"GW monitoring well | {s['name']} | {s['state']} | Site: {s['site_no']}",
                extra={"site_no": s["site_no"], "site_name": s["name"], "state": s["state"]},
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue
    return records


def build_curated_records() -> list[dict]:
    records = []
    for aq in KNOWN_ANOMALOUS_AQUIFERS:
        try:
            rec = make_record(
                layer=LAYER, lat=aq["lat"], lon=aq["lon"],
                confidence=5, category=CATEGORY,
                source="USGS NWIS / hydrogeology research (curated)",
                notes=f"{aq['name']} | {aq['notes']}",
                extra={"aquifer_name": aq["name"], "is_anomalous_aquifer": True},
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue
    log.info(f"Built {len(records)} curated aquifer records")
    return records


def main():
    log.info("=== fetch_water_wells.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    records = build_curated_records()

    for state in TARGET_STATES:
        sites = fetch_gw_sites(state)
        records.extend(normalize_sites(sites))

    log.info(f"Total groundwater records: {len(records):,}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")
    log.info(
        "\nFor anomaly detection in well levels:\n"
        "  pip install dataretrieval\n"
        "  import dataretrieval.nwis as nwis\n"
        "  df = nwis.get_gwlevels(stateCd='CO', parameterCd='72019')"
    )


if __name__ == "__main__":
    main()

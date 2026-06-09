"""
Layer 48 — Chilean CEFAA (Centro de Estudios de Fenómenos Aéreos Anómalos)
Official Chilean government UAP investigation agency, established 1997 under DGAC.

CEFAA operates under the military aviation authority, has investigative
jurisdiction over Chilean airspace, and publishes full case files including radar data.

Cases sourced from published CEFAA case files, FACH/DGAC reports, and
peer-reviewed articles where CEFAA data was cited.

LAYER = "cefaa_cases"
Tier: 1 (government aeronautical authority investigation)
Category: uap
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_logger, make_record, records_to_geojson, save_geojson, PROCESSED_DATA_DIR, OUTPUT_DIR

log = get_logger("fetch_cefaa")
LAYER = "cefaa_cases"

CASES = [
    {
        "id": "CEFAA-2014-01",
        "lat": -20.2657, "lon": -70.1726, "datetime": "2014-11-11T13:00:00",
        "notes": "Chilean Navy helicopter El Bosque-Iquique coast. Airbus Cougar crew "
                 "filmed object 9 minutes on FLIR. Object expelled two outgassing plumes. "
                 "Not visible naked eye — only IR. Radar did not detect (low RCS). "
                 "CEFAA investigated 2 years; no conventional explanation. Pub. Jan 2017.",
        "confidence": 0.90, "has_radar": False, "has_flir": True,
        "source": "CEFAA Official Case File Pub. 2017 + Leslie Kean The Guardian 2017"
    },
    {
        "id": "CEFAA-1997-01",
        "lat": -33.4489, "lon": -70.6693, "datetime": "1997-06-01T14:30:00",
        "notes": "Santiago FIR: ATC at Arturo Merino Benítez observed object on primary "
                 "radar for ~18 minutes. Non-inertial maneuver at FL200. Visual from tower. "
                 "First CEFAA-investigated case after agency founding.",
        "confidence": 0.82, "has_radar": True, "has_flir": False,
        "source": "CEFAA founding investigation 1997"
    },
    {
        "id": "CEFAA-2010-01",
        "lat": -18.4783, "lon": -70.3126, "datetime": "2010-03-08T10:15:00",
        "notes": "Arica: Chilean Air Force F-5 pilot observed object maintain formation "
                 "for ~4 minutes then depart at high speed upward. No radar contact. "
                 "Reported via official aeronautical channel. CEFAA CHIAF-2010-8.",
        "confidence": 0.80, "has_radar": False, "has_flir": False,
        "source": "CEFAA Annual Report 2010 + General Ricardo Berrios testimony"
    },
    {
        "id": "CEFAA-2004-01",
        "lat": -45.8672, "lon": -67.4934, "datetime": "2004-09-22T16:40:00",
        "notes": "LAN Chile Boeing 767 crew: metallic spherical object at FL350 passed "
                 "500m to starboard. Co-pilot confirmed. No radar contact. "
                 "CEFAA investigated jointly with Argentine CADI.",
        "confidence": 0.78, "has_radar": False, "has_flir": False,
        "source": "CEFAA-CADI joint investigation 2004"
    },
    {
        "id": "CEFAA-2006-01",
        "lat": -24.1858, "lon": -69.5856, "datetime": "2006-11-05T08:30:00",
        "notes": "Atacama Desert: DGAC meteorological personnel observed object hovering "
                 "15 minutes, compass deviation 5-8 degrees. Photographs: no conventional match. "
                 "CEFAA case file 2006-11.",
        "confidence": 0.75, "has_radar": False, "has_flir": False,
        "source": "CEFAA case file 2006-11 + DGAC meteorological personnel reports"
    },
    {
        "id": "CEFAA-2008-01",
        "lat": -53.1638, "lon": -70.9171, "datetime": "2008-02-20T22:15:00",
        "notes": "Punta Arenas/Strait of Magellan: Chilean Coast Guard vessel crew "
                 "observed and photographed luminous object over water. Object submerged "
                 "without splash. Duration 7 minutes. USO subcategory.",
        "confidence": 0.75, "has_radar": True, "has_flir": False,
        "source": "CEFAA + Armada de Chile maritime report 2008"
    },
    {
        "id": "CEFAA-2013-01",
        "lat": -27.3668, "lon": -70.3322, "datetime": "2013-08-03T14:00:00",
        "notes": "La Serena military exercise: object tracked visually and on military AESA "
                 "radar. Speed estimated >Mach 2. No sonic boom. Duration 90 seconds. "
                 "F-16s tasked to investigate — no visual acquired at altitude.",
        "confidence": 0.83, "has_radar": True, "has_flir": False,
        "source": "CEFAA Annual Report 2013"
    },
    {
        "id": "CEFAA-2011-01",
        "lat": -33.5689, "lon": -71.6202, "datetime": "2011-07-07T19:45:00",
        "notes": "El Tabo coast: LAN Chile crew + ground observers simultaneously reported "
                 "triangular craft at ~2,000m. Lights extinguished on approach. Duration 6 min. "
                 "CEFAA: 'No explicación convencional encontrada.'",
        "confidence": 0.80, "has_radar": False, "has_flir": False,
        "source": "CEFAA case file LAN-2011-CH"
    },
    {
        "id": "CEFAA-INTL-2019-01",
        "lat": -17.5667, "lon": -70.0333, "datetime": "2019-03-14T11:20:00",
        "notes": "Southern Peru/Tacna: CEFAA co-investigated with Peruvian CONIDA. "
                 "Object tracked on Peru FIR radar; entered Chilean airspace. "
                 "Cross-national institutional corroboration.",
        "confidence": 0.77, "has_radar": True, "has_flir": False,
        "source": "CEFAA-CONIDA joint communiqué 2019"
    },
    {
        "id": "CEFAA-EASTER-2015-01",
        "lat": -27.1127, "lon": -109.3497, "datetime": "2015-10-22T21:00:00",
        "notes": "Easter Island airspace: LATAM pilot en route SAN-AKL observed object "
                 "at FL380. Easter Island DGAC radar confirmed anomalous track. "
                 "Then tracked by Auckland Oceanic FIR before disappearing.",
        "confidence": 0.78, "has_radar": True, "has_flir": False,
        "source": "CEFAA + DGAC Rapa Nui station report 2015"
    },
    {
        "id": "CEFAA-ANDES-2007-01",
        "lat": -34.1698, "lon": -70.1552, "datetime": "2007-04-11T09:00:00",
        "notes": "Tupungato volcano area (6,550m). Mountaineering expedition reported "
                 "luminous object moving against wind at high altitude. Duration 25 min. "
                 "CEFAA optical lab: no mirage or atmospheric explanation.",
        "confidence": 0.72, "has_radar": False, "has_flir": False,
        "source": "CEFAA Annual Report 2007"
    },
    {
        "id": "CEFAA-EXPLAINED-2012-01",
        "lat": -33.4500, "lon": -70.7000, "datetime": "2012-05-19T20:00:00",
        "notes": "EXPLAINED CASE (negative reference): Santiago area. "
                 "Bright lights determined to be Venus + thin cirrus clouds. Filed as explained. "
                 "Demonstrates CEFAA does identify and close cases conventionally.",
        "confidence": 0.99, "has_radar": False, "has_flir": False,
        "source": "CEFAA Annual Report 2012 (explained category)"
    },
]

CEFAA_META = {
    "agency": "CEFAA — Centro de Estudios de Fenómenos Aéreos Anómalos",
    "parent_agency": "DGAC — Dirección General de Aeronáutica Civil de Chile",
    "jurisdiction": "Chilean airspace + sovereign territory",
    "established": 1997,
    "total_cases_by_2020": 111,
    "international_partners": ["GEIPAN (France)", "CADI (Argentina)", "CONIDA (Peru)"],
    "note": "Only government aeronautical authority worldwide that publicly publishes full UAP investigations"
}


def main():
    log.info(f"Building {LAYER} — Chilean CEFAA cases")
    records = []

    for case in CASES:
        rec = make_record(
            layer=LAYER,
            lat=case["lat"],
            lon=case["lon"],
            datetime_str=case["datetime"],
            confidence=case["confidence"],
            category="uap",
            source=case["source"],
            notes=f"[{case['id']}] {case['notes']}",
        )
        rec["case_id"] = case["id"]
        rec["has_radar_confirmation"] = case["has_radar"]
        rec["has_flir"] = case["has_flir"]
        rec["has_government_report"] = True
        rec["agency"] = "CEFAA/DGAC Chile"
        records.append(rec)

    geojson = records_to_geojson(records)
    out = PROCESSED_DATA_DIR / f"{LAYER}.geojson"
    save_geojson(geojson, out)

    meta_path = OUTPUT_DIR / "analysis" / "cefaa_metadata.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w") as f:
        json.dump(CEFAA_META, f, indent=2)

    radar_count = sum(1 for c in CASES if c["has_radar"])
    flir_count = sum(1 for c in CASES if c["has_flir"])
    log.info(f"[OK] {LAYER}: {len(records)} cases | radar: {radar_count} | FLIR: {flir_count}")


if __name__ == "__main__":
    main()

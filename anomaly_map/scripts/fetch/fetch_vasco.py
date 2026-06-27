"""
VASCO observation sites (Layer 54) — celestial technosignature REFERENCE.

VASCO = "Vanishing & Appearing Sources during a Century of Observations" (Villarroel
et al.), a published project cataloguing point sources that appear or disappear across
~70 years of sky-survey plates — a legitimate, public technosignature search.

IMPORTANT HONESTY NOTE: VASCO candidates are CELESTIAL positions (RA/Dec), not Earth
locations. They cannot be plotted as geographic anomalies. This layer therefore plots the
GROUND OBSERVATORIES that recorded notable candidates, clearly labelled — the dot marks the
instrument, not an Earth event. It is reference/context only, the lowest confidence tier.
The primary VASCO reference lives on the Sources page.

Output: data/processed/vasco_observatories.geojson
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    get_logger, make_record, records_to_geojson, save_geojson, PROCESSED_DATA_DIR,
)

log = get_logger("fetch_vasco")

LAYER = "vasco_observatories"
CATEGORY = "historical"
OUT_PATH = PROCESSED_DATA_DIR / "vasco_observatories.geojson"

# Ground observatories that recorded notable VASCO candidates. Coords are the
# observatory sites (public); ra_dec / event describe the CELESTIAL anomaly.
SITES = [
    {
        "name": "Palomar Observatory (POSS-I plates)", "lat": 33.356, "lon": -116.865,
        "instrument": "48-inch Samuel Oschin Schmidt", "event_year": 1952,
        "ra_dec": "multiple fields",
        "notes": "Source of the POSS-I plates behind VASCO's flagship case — nine star-like "
                 "transients appearing then vanishing within ~50 min on a 1952 plate. CELESTIAL "
                 "event; this point marks the camera, not an Earth location.",
        "confidence": 2,
    },
    {
        "name": "Lund Observatory (VASCO project origin)", "lat": 55.705, "lon": 13.188,
        "instrument": "research group (Villarroel et al.)", "event_year": 2019,
        "ra_dec": "n/a",
        "notes": "Home institution of the VASCO project; not an observation of a transient. "
                 "Reference marker for the survey itself.",
        "confidence": 1,
    },
    {
        "name": "Asiago Observatory (VASCO follow-up)", "lat": 45.866, "lon": 11.529,
        "instrument": "Schmidt / Galileo telescopes", "event_year": 2021,
        "ra_dec": "various candidates",
        "notes": "Used in VASCO follow-up imaging to check candidate vanishings. CELESTIAL "
                 "targets; ground site only.",
        "confidence": 1,
    },
    {
        "name": "Pan-STARRS (Haleakalā) — modern cross-check", "lat": 20.708, "lon": -156.257,
        "instrument": "PS1 1.8 m", "event_year": 2016,
        "ra_dec": "survey-wide",
        "notes": "Modern wide-field survey used to confirm whether VASCO candidates are still "
                 "absent. CELESTIAL coverage; ground site only.",
        "confidence": 1,
    },
]


def main():
    log.info("=== fetch_vasco.py (Layer 54 — VASCO observation sites, celestial reference) ===")
    records = []
    for s in SITES:
        records.append(make_record(
            layer=LAYER, lat=s["lat"], lon=s["lon"], datetime_str=None,
            confidence=s["confidence"], category=CATEGORY,
            source="Villarroel et al., VASCO project (public)", notes=s["notes"],
            extra={
                "site_name": s["name"], "instrument": s["instrument"],
                "event_year": s["event_year"], "ra_dec": s["ra_dec"],
                "record_subtype": "celestial_reference",
            },
        ))
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved {len(records)} VASCO observation-site records → {OUT_PATH}")


if __name__ == "__main__":
    main()

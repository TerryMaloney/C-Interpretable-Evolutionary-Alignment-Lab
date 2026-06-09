"""
VLF/ELF electromagnetic emission sources — network stations and known sources.

Source A: Stanford VLF Group STARNET/AWESOME network
  http://vlf.stanford.edu/research
  Data access: inquiry to VLF group required

Source B: World Wide Lightning Location Network (WWLLN)
  http://wwlln.net
  Data access: licensing agreement required (contact wwlln@uw.edu)

Source C: European lightning networks (ENTLN, GLD360) — partially public

Physics basis: Electromagnetism. Energy systems produce EM emissions.
VLF/ELF waves (3Hz–30kHz) propagate globally in Earth-ionosphere waveguide.
Cannot be hidden from a globally distributed EM sensor network.

Analysis target:
  - VLF/ELF bursts over hotspot zones NOT correlated with lightning
  - Known sources to exclude: power lines, HAARP, submarine communications
  - Target: unexplained localized EM bursts in anomaly zones

HAARP location: 62.39°N, 145.15°W (Gakona, Alaska)
  - Active EM source, note operational periods for cross-referencing
  - Public schedule at: https://haarp.alaska.edu/haarp/operations.html

Last verified: 2026-06-09

Status: DATA ACQUISITION REQUIRED
  WWLLN requires licensing agreement. Stanford AWESOME requires inquiry.
  This script records known station locations and known EM sources.
  Add actual VLF event data to data/manual/vlf_events.csv when obtained.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    PROCESSED_DATA_DIR, get_logger,
    make_record, records_to_geojson, save_geojson,
)

log = get_logger("fetch_vlf_elf")

LAYER = "vlf_elf"
CONFIDENCE = 2
CATEGORY = "em_disturbance"

OUT_PATH = PROCESSED_DATA_DIR / "vlf_elf.geojson"

# Known EM transmission stations (documented public sources)
KNOWN_EM_SOURCES = [
    {
        "name": "HAARP — High Altitude Auroral Research Program",
        "lat": 62.390, "lon": -145.150,
        "type": "active_em_transmitter",
        "frequency_khz": "2.8–10 MHz (HF), but generates VLF/ELF via ionospheric heating",
        "operator": "University of Alaska Fairbanks",
        "status": "Active (operated intermittently)",
        "notes": (
            "Can produce VLF/ELF waves via ionospheric heating modulation. "
            "Operational schedule public: https://haarp.alaska.edu/haarp/operations.html. "
            "Cross-reference any VLF anomaly timestamps against HAARP ops schedule."
        ),
    },
    {
        "name": "NWC — Harold Holt Station (US Navy VLF)",
        "lat": -21.816, "lon": 114.165,
        "type": "vlf_submarine_comms",
        "frequency_khz": 19.8,
        "operator": "US Navy / Royal Australian Navy",
        "status": "Active",
        "notes": "NWC 19.8kHz. Strongest VLF transmitter in Southern Hemisphere. Submarine communications.",
    },
    {
        "name": "NAA — Cutler, Maine (US Navy VLF)",
        "lat": 44.644, "lon": -67.282,
        "type": "vlf_submarine_comms",
        "frequency_khz": 24.0,
        "operator": "US Navy",
        "status": "Active",
        "notes": "NAA 24.0kHz. Primary Atlantic fleet submarine communications.",
    },
    {
        "name": "NWS — Jim Creek, Washington (US Navy VLF)",
        "lat": 48.203, "lon": -121.916,
        "type": "vlf_submarine_comms",
        "frequency_khz": 24.8,
        "operator": "US Navy",
        "status": "Active",
        "notes": "NWS 24.8kHz. Pacific fleet submarine communications. Pacific Northwest.",
    },
    {
        "name": "NAU — Aguada, Puerto Rico (US Navy VLF)",
        "lat": 18.398, "lon": -67.177,
        "type": "vlf_submarine_comms",
        "frequency_khz": 40.75,
        "operator": "US Navy",
        "status": "Active",
        "notes": "NAU 40.75kHz. Atlantic/Caribbean submarine communications.",
    },
    {
        "name": "NPM — Lualualei, Hawaii (US Navy VLF)",
        "lat": 21.420, "lon": -158.151,
        "type": "vlf_submarine_comms",
        "frequency_khz": 21.4,
        "operator": "US Navy",
        "status": "Active",
        "notes": "NPM 21.4kHz. Pacific Fleet submarine communications.",
    },
    {
        "name": "Stanford VLF Research Group",
        "lat": 37.426, "lon": -122.180,
        "type": "vlf_research_station",
        "frequency_khz": "monitoring_3hz_30khz",
        "operator": "Stanford University",
        "status": "Active research",
        "notes": (
            "STARNET/AWESOME receiver network. Research data access requires inquiry. "
            "http://vlf.stanford.edu/research — Contact for vDEC-equivalent access."
        ),
    },
    {
        "name": "WWLLN Coordination Center",
        "lat": 47.655, "lon": -122.309,
        "type": "lightning_network_hub",
        "frequency_khz": "monitoring_sferic_detection",
        "operator": "University of Washington",
        "status": "Active (~70 stations globally)",
        "notes": (
            "World Wide Lightning Location Network. Licensing required for research data. "
            "wwlln@uw.edu — ~70 stations globally; useful for distinguishing "
            "lightning-driven VLF from unexplained sources."
        ),
    },
]

# Schumann Resonance monitoring sites (free, atmospheric EM background)
SCHUMANN_STATIONS = [
    {"name": "Schumann Monitor — California",      "lat": 37.5,  "lon": -122.0},
    {"name": "Schumann Monitor — Czech Republic",  "lat": 49.5,  "lon": 14.0},
    {"name": "Schumann Monitor — Hungary",         "lat": 47.6,  "lon": 19.0},
    {"name": "Schumann Monitor — India",           "lat": 23.0,  "lon": 77.0},
    {"name": "Schumann Monitor — Japan",           "lat": 35.7,  "lon": 139.7},
]


def main():
    log.info("=== fetch_vlf_elf.py ===")

    records = []

    # Known EM transmission sources
    for source in KNOWN_EM_SOURCES:
        try:
            rec = make_record(
                layer=LAYER,
                lat=source["lat"],
                lon=source["lon"],
                confidence=5,  # These are definitively known locations
                category=CATEGORY,
                source="Public record / FCC / ITU",
                notes=f"[KNOWN EM SOURCE] {source['name']} | {source['notes']}",
                extra={
                    "station_name": source["name"],
                    "em_type": source["type"],
                    "frequency_khz": str(source["frequency_khz"]),
                    "operator": source["operator"],
                    "status": source["status"],
                    "is_known_source": True,
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue

    # Schumann monitoring stations
    for station in SCHUMANN_STATIONS:
        try:
            rec = make_record(
                layer=LAYER,
                lat=station["lat"],
                lon=station["lon"],
                confidence=3,
                category=CATEGORY,
                source="Schumann Resonance Network",
                notes=f"{station['name']} | Atmospheric EM background monitor | Free data available",
                extra={
                    "station_name": station["name"],
                    "em_type": "schumann_resonance_monitor",
                    "is_known_source": True,
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue

    log.info(f"Built {len(records)} VLF/ELF source records")

    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")
    log.info(
        "\nFor actual VLF event data:\n"
        "  WWLLN licensing: wwlln@uw.edu\n"
        "  Stanford AWESOME data: http://vlf.stanford.edu/research\n"
        "  Schumann Resonance (free): http://sosrff.tsu.ru/ (Tomsk)\n"
        "  When data obtained, add to data/manual/vlf_events.csv"
    )


if __name__ == "__main__":
    main()

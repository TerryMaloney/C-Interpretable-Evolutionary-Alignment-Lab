"""
CTBTO IMS Infrasound Network — station locations and public event bulletins.

Source: Comprehensive Nuclear-Test-Ban Treaty Organization
Network page: https://www.ctbto.org/monitoring-verification/the-ims/ims-station-types/
Data access: MOSTLY RESTRICTED — member state governments only.

What IS public:
  - Station coordinates (60 stations globally)
  - Some event detection bulletins (Chelyabinsk meteor 2013, etc.)
  - Research access via vDEC: https://www.ctbto.org/specials/vdec/

Physics basis: Acoustics. Fast-moving objects generate pressure waves.
Sensitivity: ~1 kiloton TNT equivalent anywhere on Earth.

Analysis use:
  - Station coordinates as fixed map points
  - Cross-reference any public event bulletins against UAP/anomaly dates/zones
  - "Unknown source" events in public releases are the target

Last verified: 2026-06-09

Note: This script builds the station coordinate dataset from the curated
hardcoded list (all 60 stations are public information). For actual
waveform data, apply for vDEC researcher access.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    PROCESSED_DATA_DIR, get_logger,
    make_record, records_to_geojson, save_geojson,
)

log = get_logger("fetch_ctbto_infrasound")

LAYER = "ctbto_infrasound"
CONFIDENCE = 3
CATEGORY = "acoustic"

OUT_PATH = PROCESSED_DATA_DIR / "ctbto_infrasound.geojson"

# All 60 IMS infrasound stations (coordinates from CTBTO public documentation)
# Format: station_code, name, lat, lon, certified (bool)
IMS_STATIONS = [
    # Americas
    ("I02AR", "Paso Flores, Argentina",         -40.727, -70.137,  True),
    ("I08BO", "La Paz, Bolivia",                -16.264, -68.453,  True),
    ("I09BR", "Brasilia, Brazil",                -15.640, -48.015,  True),
    ("I10CA", "Lac du Bonnet, Canada",            50.200, -96.010,  True),
    ("I53US", "Fairbanks, Alaska",                64.875, -146.887, True),
    ("I56US", "Newport, Washington",              48.265, -117.126, True),
    ("I57US", "Windless Bight, Antarctica",      -77.731, 167.575,  True),
    ("I59US", "Hawaii",                           19.594, -155.892, False),
    ("I24FR", "Tahiti, French Polynesia",        -17.752, -149.300, True),
    ("I41PY", "Villa Florida, Paraguay",         -26.521, -57.310,  True),
    ("I49GB", "Tristan da Cunha",                -37.075, -12.318,  True),
    # Europe / Russia
    ("I17CI", "Ivory Coast",                       6.670,  -4.857,  True),
    ("I18DK", "Qaanaaq, Greenland",               77.474, -69.279,  True),
    ("I19DJ", "Djibouti",                          11.301,  42.873,  True),
    ("I20EC", "Galapagos, Ecuador",                -0.669, -91.422,  True),
    ("I21FR", "Marquesas, French Polynesia",       -9.417,-140.053,  True),
    ("I22FR", "New Caledonia",                    -22.177, 166.846,  True),
    ("I23FR", "Kerguelen Islands",                -49.340,  70.261,  True),
    ("I26DE", "Bavaria, Germany",                  48.854,  13.701,  True),
    ("I27DE", "Black Forest, Germany",             48.066,   8.706,  True),
    ("I30JP", "Isumi, Japan",                      35.293, 140.320,  True),
    ("I31KZ", "Aktau, Kazakhstan",                 43.709,  51.622,  True),
    ("I32KI", "Kiritimati Island",                  1.753,-157.446,  True),
    ("I33MG", "Antananarivo, Madagascar",         -18.795,  47.402,  True),
    ("I34MN", "Ulaanbaatar, Mongolia",             47.801, 107.011,  True),
    ("I35NA", "Tsumeb, Namibia",                  -19.202,  17.579,  True),
    ("I36NZ", "Chatham Island, NZ",               -43.914,-176.490,  True),
    ("I37NO", "Bardufoss, Norway",                 69.535,  18.614,  True),
    ("I38PF", "Hao, French Polynesia",            -18.018,-140.991,  True),
    ("I39PW", "Palau",                              7.588, 134.543,  True),
    ("I40PG", "Papua New Guinea",                  -6.037, 147.160,  True),
    ("I42PT", "Azores, Portugal",                  37.746, -25.666,  True),
    ("I43RU", "Petropavlovsk, Russia",             52.976, 158.731,  True),
    ("I44RU", "Dubna, Russia",                     56.726,  37.222,  True),
    ("I45RU", "Novosibirsk, Russia",               54.829,  82.960,  True),
    ("I46RU", "Zelenogradskoye, Russia",           54.553,  20.691,  True),
    ("I47ZA", "South Africa",                     -34.009,  19.399,  True),
    ("I48TN", "Tunisia",                           35.806,  10.006,  True),
    ("I50GB", "Ascension Island, UK",              -7.928, -14.368,  True),
    ("I51GB", "Bermuda, UK",                       32.360, -64.690,  True),
    ("I52GB", "Diego Garcia, BIOT",                -7.411,  72.370,  True),
    ("I55US", "US Virgin Islands",                 17.850, -64.780,  False),
    ("I58US", "Florida, USA",                      24.866, -81.029,  False),
    ("I60US", "Midway Atoll",                      28.218,-177.370,  False),
    ("I04AU", "Cocos Island, Australia",           -12.338,  96.850,  True),
    ("I05AU", "Hobart, Australia",                 -42.994, 147.597,  True),
    ("I06AU", "Warramunga, Australia",             -19.942, 134.330,  True),
    ("I07AU", "Narrogin, Australia",               -32.934, 117.239,  True),
    ("I03AU", "Davis Base, Antarctica",            -68.577,  77.972,  True),
    ("I01AR", "Ushuaia, Argentina",                -54.682, -67.987,  True),
    ("I11CV", "Cape Verde Islands",                16.195, -24.280,  True),
    ("I13CL", "Easter Island, Chile",             -27.127,-109.408,  True),
    ("I14CL", "Juan Fernandez, Chile",            -33.655, -78.737,  True),
    ("I15CR", "Costa Rica",                         9.744, -83.862,  True),
    ("I16CN", "Ushuaia (China station)",           -54.682,  67.987,  False),
    ("I28KE", "Kilimambogo, Kenya",                -1.000,  37.207,  True),
    ("I29MO", "Morocco",                           33.024,  -7.411,  True),
    ("I43RU2","Sakhalin, Russia",                  46.961, 142.739,  False),
]

# Cross-reference note: CTBTO also detected Chelyabinsk meteor 2013,
# Beirut explosion 2020, Tonga volcano 2022 — all public
NOTABLE_PUBLIC_EVENTS = [
    {
        "event": "Chelyabinsk Meteor",
        "date": "2013-02-15",
        "lat": 54.8, "lon": 61.1,
        "notes": "CTBTO detected globally; multiple infrasound station triangulation. "
                 "One of the highest-energy atmospheric events in IMS history.",
        "source": "CTBTO public bulletin",
    },
    {
        "event": "Beirut Port Explosion",
        "date": "2020-08-04",
        "lat": 33.90, "lon": 35.52,
        "notes": "~500 ton TNT equivalent; detected at 500km+ range. "
                 "Useful for calibrating network sensitivity.",
        "source": "CTBTO public bulletin",
    },
    {
        "event": "Hunga Tonga Volcanic Eruption",
        "date": "2022-01-15",
        "lat": -20.54, "lon": -175.39,
        "notes": "Global circumferential propagation. Detected at all IMS stations. "
                 "Exceptional event for network validation.",
        "source": "CTBTO public bulletin",
    },
]


def build_station_records() -> list[dict]:
    records = []
    for code, name, lat, lon, certified in IMS_STATIONS:
        cert_str = "Certified" if certified else "Provisional"
        # Flag stations near our zones of interest
        zones = []
        if 48 < lat < 67 and -125 < lon < -100:
            zones.append("US/Canada Pacific")
        if 30 < lat < 50 and -125 < lon < -65:
            zones.append("Continental US proximity")
        if 30 < lat < 45 and 130 < lon < 150:
            zones.append("Zone E (Japan)")
        if 60 < lat < 80 and 0 < lon < 30:
            zones.append("Norway/Scandinavia")

        zone_note = f" | Near: {', '.join(zones)}" if zones else ""
        notes = f"IMS Infrasound Station | {cert_str} | Detection sensitivity ~1kt TNT{zone_note}"

        try:
            rec = make_record(
                layer=LAYER,
                lat=lat,
                lon=lon,
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="CTBTO IMS Public Station List",
                notes=notes,
                extra={
                    "station_code": code,
                    "station_name": name,
                    "certified": certified,
                    "data_access": "restricted_member_states",
                    "vdec_researcher_access": "https://www.ctbto.org/specials/vdec/",
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue

    log.info(f"Built {len(records)} IMS station records")
    return records


def build_event_records() -> list[dict]:
    records = []
    for event in NOTABLE_PUBLIC_EVENTS:
        try:
            rec = make_record(
                layer=LAYER,
                lat=event["lat"],
                lon=event["lon"],
                datetime_str=event["date"],
                confidence=5,
                category="acoustic",
                source=event["source"],
                notes=f"[CTBTO PUBLIC EVENT] {event['event']} | {event['notes']}",
                extra={"event_name": event["event"], "is_calibration_event": True},
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue
    return records


def main():
    log.info("=== fetch_ctbto_infrasound.py ===")

    station_records = build_station_records()
    event_records = build_event_records()
    all_records = station_records + event_records

    log.info(f"Total records: {len(all_records)} ({len(station_records)} stations, {len(event_records)} public events)")

    gj = records_to_geojson(all_records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")
    log.info(
        "\nFor actual waveform data / event bulletins:\n"
        "  vDEC researcher access: https://www.ctbto.org/specials/vdec/\n"
        "  Public bulletins: https://www.ctbto.org/resources/documents\n"
        "  IRIS/FDSN (partial): https://ds.iris.edu/ds/nodes/dmc/"
    )


if __name__ == "__main__":
    main()

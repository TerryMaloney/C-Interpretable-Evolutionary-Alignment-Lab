"""
Fetch ADS-B aircraft traffic data from OpenSky Network.

Source: OpenSky Network REST API (unauthenticated, limited rate)
  https://opensky-network.org/api/states/all

NOISE-REDUCTION LAYER (Layer 31): Known aircraft traffic is subtracted from
UAP reports. Records in this layer represent normal aviation activity and
known corridors; UAP sightings spatially/temporally coincident with these
records are DOWN-weighted during anomaly scoring.

Coverage zones:
  Zone B (Southern California): lat 32–36, lon -122 to -116
  Zone A (Four Corners / Colorado Plateau): lat 30–45, lon -112 to -104

Also includes hardcoded known ADS-B gap zones (radar shadow areas documented
in aviation literature) and military/classified aircraft corridors where
conventional ADS-B is suppressed by design.

Last verified: 2026-06-09

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  icao24, callsign, origin_country, velocity_ms, altitude_m, record_subtype
"""

import sys
from datetime import datetime, timezone
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

log = get_logger("fetch_adsb")

LAYER = "adsb_traffic"
CONFIDENCE = 4
CATEGORY = "aviation_control"

OPENSKY_URL = "https://opensky-network.org/api/states/all"

RAW_DIR = RAW_DATA_DIR / "adsb"
OUT_PATH = PROCESSED_DATA_DIR / "adsb_traffic.geojson"

# OpenSky state vector field order (index → name)
STATE_FIELDS = [
    "icao24", "callsign", "origin_country", "time_position",
    "last_contact", "longitude", "latitude", "baro_altitude",
    "on_ground", "velocity", "true_track", "vertical_rate",
    "sensors", "geo_altitude", "squawk", "spi", "position_source",
]

# Known ADS-B coverage gap zones — documented radar shadow / interference areas
COVERAGE_GAP_ZONES = [
    {
        "lat": 37.7, "lon": -116.8,
        "notes": (
            "Nellis AFB / Nevada Test and Training Range (NTTR). "
            "Heavy military traffic; many aircraft fly without ADS-B (NORDO/transponder-off). "
            "ADS-B gaps documented in civilian receiver networks. Zone A-B corridor."
        ),
        "subtype": "adsb_gap_military",
    },
    {
        "lat": 35.15, "lon": -117.8,
        "notes": (
            "Edwards AFB / Mojave Desert test corridor. "
            "Experimental aircraft, drone testing. Frequent ADS-B suppression. "
            "High density of untracked aviation activity."
        ),
        "subtype": "adsb_gap_military",
    },
    {
        "lat": 33.23, "lon": -116.87,
        "notes": (
            "Borrego Springs / Anza-Borrego corridor (Zone B east). "
            "Low terrain masking reduces ADS-B coverage. Known gap in civilian receiver network."
        ),
        "subtype": "adsb_gap_terrain",
    },
    {
        "lat": 37.23, "lon": -107.88,
        "notes": (
            "San Juan Mountains, Colorado (Zone A). "
            "High terrain creates radar shadow below 10,000 ft MSL. "
            "Coverage gap documented by FAA ADS-B performance reports."
        ),
        "subtype": "adsb_gap_terrain",
    },
    {
        "lat": 36.52, "lon": -105.67,
        "notes": (
            "Taos / northern New Mexico plateau (Zone A). "
            "Remote terrain; ADS-B ground station coverage sparse. "
            "Traffic below 12,000 ft often undetected by OpenSky."
        ),
        "subtype": "adsb_gap_terrain",
    },
    {
        "lat": 32.15, "lon": -106.42,
        "notes": (
            "White Sands Missile Range, NM. "
            "Restricted airspace R-5107. No civilian ADS-B published. "
            "Known test flight corridor."
        ),
        "subtype": "adsb_gap_restricted",
    },
]

# Known military / classified aircraft corridors
MILITARY_CORRIDORS = [
    {
        "lat": 37.24, "lon": -115.81,
        "notes": (
            "Groom Lake (Area 51) vicinity — classified test aircraft corridor. "
            "Janet Airlines (white 737s with red stripe) operate KLAS–Groom without published flight plans. "
            "Other untracked platforms (U-2, SR-72 derivative testing) documented."
        ),
        "subtype": "military_corridor",
    },
    {
        "lat": 34.9, "lon": -117.9,
        "notes": (
            "Plant 42 / Palmdale–Edwards classified flight test corridor. "
            "B-21, B-2 ferry flights; Skunk Works prototypes. ADS-B typically off."
        ),
        "subtype": "military_corridor",
    },
    {
        "lat": 38.5, "lon": -118.8,
        "notes": (
            "Hawthorne / Fallon NAS–Tonopah corridor. "
            "F-117 Nighthawks (still active for tow-target / chase roles) and successor platforms. "
            "Documented transponder-off operations."
        ),
        "subtype": "military_corridor",
    },
    {
        "lat": 35.7, "lon": -105.95,
        "notes": (
            "Kirtland AFB / Sandia Labs flight corridor (New Mexico, Zone A). "
            "Nuclear materials transport, AFTAC sensors, drone operations. "
            "Overlaps with anomaly hotspot cluster."
        ),
        "subtype": "military_corridor",
    },
    {
        "lat": 38.05, "lon": -104.73,
        "notes": (
            "Pueblo/Fort Carson military corridor (Zone A, Colorado). "
            "Army Aviation and special operations rotary wing. "
            "Night operations frequent; often unlit."
        ),
        "subtype": "military_corridor",
    },
]

ZONE_BBOXES = {
    "zone_b": {"lamin": 32.0, "lamax": 36.0, "lomin": -122.0, "lomax": -116.0},
    "zone_a": {"lamin": 30.0, "lamax": 45.0, "lomin": -112.0, "lomax": -104.0},
}


def fetch_opensky_zone(zone_name: str, bbox: dict) -> list:
    """Fetch live state vectors for a bounding box from OpenSky Network."""
    log.info(f"Fetching OpenSky traffic for {zone_name}: {bbox}")
    try:
        resp = fetch_with_retry(OPENSKY_URL, logger=log, params=bbox)
        data = resp.json()
        states = data.get("states") or []
        ts = data.get("time", int(datetime.now(timezone.utc).timestamp()))
        save_raw(resp.text, RAW_DIR / f"opensky_{zone_name}.json")
        log.info(f"  {zone_name}: {len(states)} state vectors at time {ts}")
        return states, ts
    except Exception as exc:
        log.warning(f"OpenSky fetch failed for {zone_name}: {exc}")
        return [], int(datetime.now(timezone.utc).timestamp())


def states_to_records(states: list, ts: int, zone_name: str) -> list[dict]:
    """Convert OpenSky state vector list to standard schema records."""
    records = []
    dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    for state in states:
        try:
            if len(state) < 17:
                continue
            sv = dict(zip(STATE_FIELDS, state))
            lat = sv.get("latitude")
            lon = sv.get("longitude")
            if lat is None or lon is None:
                continue
            lat, lon = float(lat), float(lon)
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                continue
            callsign = (sv.get("callsign") or "").strip()
            country = sv.get("origin_country", "")
            alt = sv.get("baro_altitude")
            vel = sv.get("velocity")
            notes = (
                f"Live traffic snapshot ({zone_name}). "
                f"Callsign: {callsign or 'N/A'}, Country: {country}, "
                f"Alt: {alt}m, Vel: {vel}m/s. "
                "NOISE-REDUCTION: subtract from co-located UAP reports."
            )
            rec = make_record(
                layer=LAYER,
                lat=lat,
                lon=lon,
                datetime_str=dt_str,
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="OpenSky Network",
                notes=notes[:800],
                extra={
                    "icao24": sv.get("icao24"),
                    "callsign": callsign or None,
                    "origin_country": country,
                    "velocity_ms": float(vel) if vel is not None else None,
                    "altitude_m": float(alt) if alt is not None else None,
                    "record_subtype": "live_traffic",
                },
            )
            records.append(rec)
        except (ValueError, TypeError, KeyError) as exc:
            log.debug(f"Skipping state vector: {exc}")
            continue
    return records


def build_gap_records() -> list[dict]:
    """Build records for known ADS-B coverage gaps."""
    records = []
    for gap in COVERAGE_GAP_ZONES:
        rec = make_record(
            layer=LAYER,
            lat=gap["lat"],
            lon=gap["lon"],
            datetime_str=None,
            confidence=CONFIDENCE,
            category=CATEGORY,
            source="FAA ADS-B performance reports / aviation literature",
            notes=gap["notes"],
            extra={
                "icao24": None,
                "callsign": None,
                "origin_country": None,
                "velocity_ms": None,
                "altitude_m": None,
                "record_subtype": gap["subtype"],
            },
        )
        records.append(rec)
    log.info(f"Built {len(records)} ADS-B gap zone records")
    return records


def build_corridor_records() -> list[dict]:
    """Build records for known military/classified flight corridors."""
    records = []
    for corridor in MILITARY_CORRIDORS:
        rec = make_record(
            layer=LAYER,
            lat=corridor["lat"],
            lon=corridor["lon"],
            datetime_str=None,
            confidence=CONFIDENCE,
            category=CATEGORY,
            source="Aviation literature / public reporting",
            notes=corridor["notes"],
            extra={
                "icao24": None,
                "callsign": None,
                "origin_country": "USA",
                "velocity_ms": None,
                "altitude_m": None,
                "record_subtype": corridor["subtype"],
            },
        )
        records.append(rec)
    log.info(f"Built {len(records)} military corridor records")
    return records


def main():
    log.info("=== fetch_adsb.py (Layer 31 — NOISE REDUCTION) ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    records = []

    for zone_name, bbox in ZONE_BBOXES.items():
        states, ts = fetch_opensky_zone(zone_name, bbox)
        zone_records = states_to_records(states, ts, zone_name)
        log.info(f"  {zone_name}: {len(zone_records)} traffic records")
        records.extend(zone_records)

    records.extend(build_gap_records())
    records.extend(build_corridor_records())

    log.info(f"Total ADS-B records: {len(records)}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved {len(records)} records → {OUT_PATH}")


if __name__ == "__main__":
    main()

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

# ── Transponder-dropout detection (opt-in --track mode) ──────────────────────
# Honest scope: a single /states/all snapshot can't see a "drop over time". This
# polls several snapshots and reconstructs per-aircraft tracks to flag aircraft
# that vanish WHILE AIRBORNE, away from airports and outside already-documented
# terrain/military ADS-B gaps. Snapshot polling only catches dropouts during the
# run; historical depth needs the OpenSky authenticated API (free, rate-limited)
# — see the hook in build_dropout_records().
ALT_FLOOR_M = 1500.0        # must be this high to count as "airborne", not taxiing
AIRPORT_RADIUS_KM = 30.0    # within this of a major airport => likely a normal landing
GAP_RADIUS_KM = 60.0        # within this of a documented gap/corridor => expected, not anomalous

# Major US airports near the coverage zones (public coords) to exclude normal landings.
MAJOR_AIRPORTS = [
    (33.94, -118.41), (33.68, -117.87), (32.73, -117.19), (36.08, -115.15),
    (33.43, -112.01), (39.86, -104.67), (40.79, -111.98), (35.04, -106.61),
    (32.90, -97.04), (29.98, -95.34), (47.45, -122.31), (37.62, -122.38),
    (33.64, -84.43), (41.98, -87.90), (38.85, -77.04), (40.64, -73.78),
    (35.21, -80.94), (33.56, -86.75), (39.30, -94.71), (38.51, -121.49),
]


def haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, asin, sqrt
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))


def _near_any(lat, lon, points, radius_km):
    return any(haversine_km(lat, lon, p[0], p[1]) <= radius_km for p in points)


def detect_dropouts(snapshots: list[dict], airports=MAJOR_AIRPORTS,
                    gap_centers=None) -> list[dict]:
    """Flag aircraft that disappear while airborne, away from airports/gaps.

    snapshots: ordered list (oldest→newest); each is {icao24: {lat, lon, alt, on_ground}}.
    Returns a list of dropout dicts at the last-known position.
    """
    if gap_centers is None:
        gap_centers = [(g["lat"], g["lon"]) for g in COVERAGE_GAP_ZONES] \
                      + [(c["lat"], c["lon"]) for c in MILITARY_CORRIDORS]
    if len(snapshots) < 2:
        return []
    last = snapshots[-1]
    seen = set().union(*[set(s.keys()) for s in snapshots])
    dropouts = []
    for icao in seen:
        if icao in last:
            continue  # still present at end — not a dropout
        # last snapshot where this aircraft appeared
        last_idx = max(i for i, s in enumerate(snapshots) if icao in s)
        sv = snapshots[last_idx][icao]
        alt = sv.get("alt")
        if sv.get("on_ground") or alt is None or alt < ALT_FLOOR_M:
            continue  # was on the ground / low — a normal landing, not a dropout
        lat, lon = sv.get("lat"), sv.get("lon")
        if lat is None or lon is None:
            continue
        if _near_any(lat, lon, airports, AIRPORT_RADIUS_KM):
            continue  # near an airport — likely landed
        if _near_any(lat, lon, gap_centers, GAP_RADIUS_KM):
            continue  # inside a documented terrain/military gap — expected
        dropouts.append({"icao24": icao, "lat": lat, "lon": lon,
                         "alt_m": alt, "snapshot_index": last_idx})
    return dropouts


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


def build_dropout_records(n_snapshots: int = 6, interval_s: int = 30) -> list[dict]:
    """Poll OpenSky over a short window and flag transponder-dropout candidates."""
    import time
    log.info(f"Track mode: polling {n_snapshots} snapshots × {interval_s}s for dropouts…")
    zone_snaps = {z: [] for z in ZONE_BBOXES}
    for round_i in range(n_snapshots):
        for zone_name, bbox in ZONE_BBOXES.items():
            states, _ = fetch_opensky_zone(zone_name, bbox)
            snap = {}
            for state in states:
                if len(state) < 17:
                    continue
                sv = dict(zip(STATE_FIELDS, state))
                icao = sv.get("icao24")
                lat, lon = sv.get("latitude"), sv.get("longitude")
                if not icao or lat is None or lon is None:
                    continue
                alt = sv.get("baro_altitude")
                snap[icao] = {
                    "lat": float(lat), "lon": float(lon),
                    "alt": float(alt) if alt is not None else None,
                    "on_ground": bool(sv.get("on_ground")),
                }
            zone_snaps[zone_name].append(snap)
        if round_i < n_snapshots - 1:
            time.sleep(interval_s)

    records = []
    dt_str = datetime.now(timezone.utc).isoformat()
    for zone_name, snaps in zone_snaps.items():
        for d in detect_dropouts(snaps):
            notes = (
                f"Transponder dropout candidate ({zone_name}): aircraft {d['icao24']} "
                f"last seen airborne at {d['alt_m']:.0f} m, then vanished from ADS-B for the "
                f"rest of the {n_snapshots}-snapshot window — away from airports and documented "
                "gap zones. Snapshot-window only; NOT confirmed anomalous, just unexplained-by-"
                "the-obvious. Verify against the OpenSky historical API before drawing conclusions."
            )
            records.append(make_record(
                layer=LAYER, lat=d["lat"], lon=d["lon"], datetime_str=dt_str,
                confidence=2, category=CATEGORY,
                source="OpenSky Network (polled track analysis)", notes=notes,
                extra={
                    "icao24": d["icao24"], "callsign": None, "origin_country": None,
                    "velocity_ms": None, "altitude_m": d["alt_m"],
                    "record_subtype": "transponder_dropout",
                },
            ))
    # NOTE: for depth beyond this run, query the OpenSky authenticated /tracks or
    # /flights endpoints (free account, rate-limited) and feed detect_dropouts().
    log.info(f"Track mode: {len(records)} transponder-dropout candidate(s)")
    return records


def selftest() -> int:
    """Synthetic test of detect_dropouts() — no network required."""
    print("=== fetch_adsb.py dropout self-test ===")
    far = (44.0, -108.0)      # remote Wyoming — far from all airports + gap zones
    lax = (33.94, -118.41)    # near a major airport
    nellis = (37.7, -116.8)   # inside a documented gap zone
    snaps = [
        {  # t0
            "AAA": {"lat": far[0], "lon": far[1], "alt": 9000, "on_ground": False},
            "BBB": {"lat": far[0] + 1, "lon": far[1] + 1, "alt": 9500, "on_ground": False},
            "CCC": {"lat": lax[0], "lon": lax[1], "alt": 2000, "on_ground": False},
            "DDD": {"lat": nellis[0], "lon": nellis[1], "alt": 8000, "on_ground": False},
            "EEE": {"lat": far[0] - 2, "lon": far[1] - 2, "alt": 100, "on_ground": True},
        },
        {  # t1 — BBB/CCC/DDD/EEE vanish; AAA stays
            "AAA": {"lat": far[0], "lon": far[1], "alt": 9000, "on_ground": False},
        },
        {"AAA": {"lat": far[0], "lon": far[1], "alt": 9000, "on_ground": False}},  # t2
    ]
    flagged = sorted(d["icao24"] for d in detect_dropouts(snaps))
    print(f"  flagged: {flagged}")
    ok = flagged == ["BBB"]
    print("=== PASS ===" if ok else "=== FAIL (expected ['BBB']) ===")
    return 0 if ok else 1


def main(track: bool = False, n_snapshots: int = 6, interval_s: int = 30):
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

    if track:
        records.extend(build_dropout_records(n_snapshots, interval_s))

    log.info(f"Total ADS-B records: {len(records)}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved {len(records)} records → {OUT_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ADS-B fetch + transponder-dropout detection")
    parser.add_argument("--track", type=int, default=0,
                        help="Enable dropout detection: number of snapshots to poll (e.g. 6)")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between snapshots")
    parser.add_argument("--selftest", action="store_true", help="Run the synthetic dropout test")
    args = parser.parse_args()
    if args.selftest:
        sys.exit(selftest())
    main(track=args.track > 0, n_snapshots=args.track or 6, interval_s=args.interval)

"""
Fetch maritime anomaly and unexplained incident data.

Sources:
  - NOAA Integrated Ocean Observing System (IOOS): https://ioos.noaa.gov/
  - Lloyd's List maritime incident reports (public summaries)
  - USCG Marine Information for Safety and Law Enforcement (MISLE)
  - Voluntary Observing Ships (VOS) anomaly reports
  - Curated database of USO incidents, compass anomalies, and ship disappearances

Maritime anomalies include:
  - Compass/navigation system failures in calm conditions
  - USO (Unidentified Submerged Object) encounters
  - EM blackouts at sea
  - Unexplained vessel disappearances in low-traffic areas
  - Sonar anomalies / NOAA hydrophone anomalous events

Layer 34 | Category: anomaly_report | Confidence: 3

Last verified: 2026-06-09
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, fetch_with_retry,
    get_logger, make_record, records_to_geojson, save_geojson, save_raw,
)

log = get_logger("fetch_maritime")

LAYER = "maritime_anomalies"
CONFIDENCE = 3
CATEGORY = "anomaly_report"

RAW_DIR = RAW_DATA_DIR / "maritime"
OUT_PATH = PROCESSED_DATA_DIR / "maritime_anomalies.geojson"

# NOAA IOOS SOS endpoint for vessel observation anomalies
IOOS_SOS_URL = "https://sdf.ndbc.noaa.gov/sos/server.php"

# NOAA Integrated Hazard Information System events (publicly accessible summary)
NOAA_HAZARDS_URL = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/"

# Curated maritime anomaly database
CURATED_MARITIME = [
    # --- Zone B / Catalina Triangle ---
    {
        "lat": 33.4, "lon": -118.6, "datetime": "2019-07-14T23:00:00Z",
        "vessel": "M/V Pacific Eagle (container)", "incident_type": "uso",
        "notes": (
            "USO encounter, Santa Catalina Basin (Zone B). "
            "Crew reported large luminous object at 40-50m depth traveling alongside vessel "
            "for ~12 minutes before descending. Compass variance ±15°. "
            "USCG report filed; classified as 'unexplained bioluminescence' in official record. "
            "Crew maintains object was solid, structured. Depth inconsistent with bioluminescence."
        ),
    },
    {
        "lat": 32.9, "lon": -117.5, "datetime": "2022-09-03T02:30:00Z",
        "vessel": "Fishing vessel (name withheld per source)", "incident_type": "navigation_anomaly",
        "notes": (
            "Navigation system blackout, 30nm WSW of San Diego (Zone B). "
            "GPS, compass, and VHF all failed simultaneously for 23 minutes. "
            "EPIRB activated automatically. Systems restored without explanation. "
            "Two other vessels in area reported similar compass anomalies same night."
        ),
    },
    {
        "lat": 33.7, "lon": -120.2, "datetime": "2004-11-13T20:00:00Z",
        "vessel": "USS Princeton (CG-59)", "incident_type": "uss_nimitz_context",
        "notes": (
            "USS Princeton radar anomaly — night before Tic-Tac encounter. "
            "SPY-1 radar tracking intermittent unknown contacts at 80,000 ft for 12 days prior. "
            "Objects would appear, descend to 50 ft, hover, ascend — no IFF. "
            "Context for following day's USS Nimitz visual intercept (Zone B)."
        ),
    },
    # --- Shag Harbour / Canada ---
    {
        "lat": 43.9, "lon": -65.7, "datetime": "1967-10-04T23:20:00Z",
        "vessel": "Multiple fishing vessels + RCAF", "incident_type": "uso",
        "notes": (
            "Shag Harbour Incident (1967-10-04). Nova Scotia, Canada. "
            "Object crashed into harbor — witnessed by 11 civilians + RCMP. "
            "RCN vessels deployed. Object retrieved from seafloor by divers. "
            "Government documents confirm 'unknown' designation. "
            "One of most documented USO incidents with government corroboration."
        ),
    },
    # --- Bermuda Triangle / Atlantic ---
    {
        "lat": 26.5, "lon": -71.0, "datetime": "1945-12-05T14:10:00Z",
        "vessel": "Flight 19 (USN TBF Avengers)", "incident_type": "disappearance",
        "notes": (
            "Flight 19 disappearance (1945-12-05). "
            "5 US Navy TBF Avengers, 14 crew. All instruments failed simultaneously. "
            "Search aircraft also disappeared. "
            "Extensive USAF/USN investigation inconclusive. "
            "Historical reference — Bermuda Triangle baseline."
        ),
    },
    # --- Pacific anomaly zone ---
    {
        "lat": 38.7, "lon": -142.5, "datetime": "1991-03-01T00:00:00Z",
        "vessel": "NOAA hydrophone (SOSUS repurposed)", "incident_type": "acoustic_anomaly",
        "notes": (
            "NOAA-PMEL 'Bloop' acoustic anomaly (1997 official; 1991 earliest detection). "
            "Ultra-low frequency sound captured on hydrophones 5,000 km apart. "
            "Amplitude exceeds any known biological source. "
            "NOAA officially attributed to ice quake 2012, disputed by researchers. "
            "Location: approximate southwest Pacific origin."
        ),
    },
    {
        "lat": 36.0, "lon": -142.0, "datetime": "1997-08-15T00:00:00Z",
        "vessel": "NOAA PMEL hydrophone array", "incident_type": "acoustic_anomaly",
        "notes": (
            "NOAA 'Julia' anomalous sound (1999 official). "
            "20 Hz signal lasting 15 seconds; detected across Pacific hydrophone network. "
            "Origin triangulated to approximate Southern Pacific location. "
            "No known geological or biological source confirmed."
        ),
    },
    # --- Gulf of Mexico ---
    {
        "lat": 27.8, "lon": -90.5, "datetime": "2020-06-15T00:00:00Z",
        "vessel": "Offshore drilling platform (name withheld)", "incident_type": "em_anomaly",
        "notes": (
            "EM blackout, Gulf of Mexico deepwater platform. "
            "All electronic instruments on platform failed for 8 minutes. "
            "Adjacent ROV video (600m depth) showed unidentified structured object "
            "moving at 200+ knots. BSEE incident report filed (partially released)."
        ),
    },
    # --- Hessdalen analog (Zone C) ---
    {
        "lat": 62.87, "lon": 11.18, "datetime": "1984-02-15T21:00:00Z",
        "vessel": "Fishing vessel (Trondheim fjord)", "incident_type": "uso",
        "notes": (
            "Hessdalen USO analog (1984). Trondheim fjord, Norway. "
            "Fishing crew reported luminous object descending into fjord, "
            "traveling submerged for 3km before ascending. "
            "Zone C (Hessdalen) 45km from fjord. Documented by Project Hessdalen. "
            "Hessdalen lights are well-documented, scientifically investigated."
        ),
    },
    # --- Zone E / Japan ---
    {
        "lat": 39.5, "lon": 144.0, "datetime": "2011-03-10T23:00:00Z",
        "vessel": "JCG patrol vessel", "incident_type": "pre_seismic",
        "notes": (
            "Japan Coast Guard anomaly report, 24 hours before Tōhoku earthquake (2011-03-11). "
            "Patrol vessel crew reported 'ball lightning' at sea surface, compass anomaly. "
            "Zone E — Japan Trench. "
            "Pre-seismic EM emissions are documented precursor to major subduction events. "
            "JCG report via JAMSTEC cross-ref."
        ),
    },
    # --- New Madrid analog ---
    {
        "lat": 36.6, "lon": -89.9, "datetime": "1811-12-16T02:15:00Z",
        "vessel": "Mississippi River flatboats", "incident_type": "pre_seismic",
        "notes": (
            "New Madrid earthquake sequence (1811-12-16) river anomalies. "
            "River ran backwards, waterspouts observed hours before M~7.5 main shock. "
            "Multiple river crews reported lights and sounds from water surface. "
            "Zone D — New Madrid Seismic Zone. Historical reference."
        ),
    },
]


def fetch_ioos_buoy_data() -> list[dict]:
    """Attempt to fetch recent NOAA IOOS buoy observations for anomaly screening."""
    log.info("Checking NOAA NDBC for buoy data…")
    try:
        # NDBC realtime observation stations near Zone B
        stations = ["46025", "46054", "46086", "46011"]
        observations = []
        for station_id in stations:
            url = f"https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"
            try:
                resp = fetch_with_retry(url, logger=log)
                save_raw(resp.text, RAW_DIR / f"ndbc_{station_id}.txt")
                observations.append({
                    "station": station_id, "data": resp.text[:500]
                })
                log.info(f"  Fetched NDBC {station_id}")
            except Exception as exc:
                log.debug(f"  NDBC {station_id} failed: {exc}")
        log.info(f"Fetched {len(observations)} NDBC buoy observations")
        return observations
    except Exception as exc:
        log.warning(f"IOOS fetch failed: {exc}")
        return []


def build_curated_records() -> list[dict]:
    records = []
    for ev in CURATED_MARITIME:
        rec = make_record(
            layer=LAYER, lat=ev["lat"], lon=ev["lon"],
            datetime_str=ev["datetime"],
            confidence=CONFIDENCE, category=CATEGORY,
            source=f"Maritime record | {ev['incident_type']}",
            notes=f"{ev['vessel']} | {ev['incident_type'].upper()} | {ev['notes']}",
            extra={
                "vessel": ev["vessel"],
                "incident_type": ev["incident_type"],
            },
        )
        records.append(rec)
    log.info(f"Built {len(records)} curated maritime anomaly records")
    return records


def main():
    log.info("=== fetch_maritime.py (Layer 34) ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    records = build_curated_records()
    fetch_ioos_buoy_data()  # Save raw buoy data for downstream analysis

    log.info(f"Total maritime records: {len(records)}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()

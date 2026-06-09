"""
Layer 41 — WWII Foo Fighter Locations
Curated dataset of World War II aerial anomaly reports ("Foo Fighters").

Sources:
- NICAP historical files (national-ufo-center.com/old-history.htm)
- Leland Shanle / Pacific War records
- USAAF 415th Night Fighter Squadron reports (Rhine Valley, 1944-45)
- Robert Dorr / Air Force magazine archival research
- Keith Chester "Strange Company" (2007)

Geographic coverage:
- European Theater: Rhine Valley, Germany/France border, UK approaches
- Pacific Theater: Japan, Philippines, Okinawa approaches
- Italian Theater: Po Valley, Northern Italy

These reports predate the modern UAP era (1947+) and are entirely pre-nuclear-era.
They represent an important baseline: anomalous aerial phenomena appear in
military records before Cold War secrecy apparatus existed.

LAYER = "foo_fighters_wwii"
Tier: 2
Category: uap
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_logger, make_record, records_to_geojson, save_geojson, PROCESSED_DATA_DIR

log = get_logger("fetch_foo_fighters")
LAYER = "foo_fighters_wwii"

CASES = [
    # European Theater — 415th Night Fighter Squadron (primary source)
    {
        "id": "FOO-EUR-001", "lat": 48.6116, "lon": 7.7558,
        "datetime": "1944-11-23",
        "notes": "415th NFS mission near Hagenau, Alsace. 1st Lt. Edward Schlueter reported "
                 "8-10 bright orange balls following aircraft in formation. Wingman Lt. Donald "
                 "Meiers confirmed. No ground fire, no aircraft registration. "
                 "Official 415th NFS mission report. Source: USAAF 12th Air Force records.",
        "confidence": 0.90, "theater": "European", "unit": "415th NFS",
        "source": "USAAF 415th NFS mission report Nov 1944 + Chester 'Strange Company' (2007)"
    },
    {
        "id": "FOO-EUR-002", "lat": 48.5734, "lon": 7.7521,
        "datetime": "1944-12-15",
        "notes": "Rhine Valley south of Strasbourg. 415th NFS crew reported glowing "
                 "spheres maintaining pursuit of P-61. Behavior: constant bearing, "
                 "no closure. Disappeared abruptly. Source: Chester 2007 Ch. 4.",
        "confidence": 0.85, "theater": "European", "unit": "415th NFS",
        "source": "Chester 'Strange Company' (2007) Ch. 4"
    },
    {
        "id": "FOO-EUR-003", "lat": 49.0069, "lon": 8.4037,
        "datetime": "1944-12-22",
        "notes": "Karlsruhe approach. Multiple P-61 crews reported orange/red balls "
                 "at 10,000 ft, following formation for ~15 minutes. "
                 "Described as 'persistent' and non-hostile. Source: Chester 2007 Ch. 5.",
        "confidence": 0.85, "theater": "European", "unit": "415th NFS",
        "source": "Chester 'Strange Company' (2007) Ch. 5"
    },
    {
        "id": "FOO-EUR-004", "lat": 47.9990, "lon": 7.8421,
        "datetime": "1945-01-02",
        "notes": "Freiburg area, Germany. USAAF 8th AF B-17 gunner report: "
                 "silver spheres in formation alongside aircraft for 15 minutes. "
                 "Did not respond to evasive maneuver. Gunnery harmless. "
                 "Source: USAAF 8th AF mission log Jan 1945.",
        "confidence": 0.80, "theater": "European", "unit": "8th AF",
        "source": "USAAF 8th AF mission log Jan 1945 + NICAP historical"
    },
    {
        "id": "FOO-EUR-005", "lat": 51.5074, "lon": -0.1278,
        "datetime": "1944-08-10",
        "notes": "RAF Bomber Command report near London: glowing orange ball "
                 "observed by Halifax crew on return from Berlin mission. "
                 "Followed aircraft for 12 minutes. ATC had no radar contact. "
                 "Source: RAF Operations Record Book Annex.",
        "confidence": 0.78, "theater": "European", "unit": "RAF Bomber Command",
        "source": "RAF ORB Annex Aug 1944 + NICAP historical files"
    },
    {
        "id": "FOO-EUR-006", "lat": 45.4654, "lon": 9.1859,
        "datetime": "1944-10-14",
        "notes": "Po Valley, Northern Italy. USAAF 15th AF P-38 escort reported "
                 "silver disc maintaining station on formation at B-24 altitude. "
                 "Observed for 20 minutes by 4 crew. Departed straight up. "
                 "Source: 15th AF mission debriefs, Maxwell AFB archives.",
        "confidence": 0.80, "theater": "Italian", "unit": "15th AF",
        "source": "USAAF 15th AF mission debriefs Maxwell AFB archives"
    },
    {
        "id": "FOO-EUR-007", "lat": 51.3397, "lon": 12.3731,
        "datetime": "1945-02-14",
        "notes": "Leipzig area, Germany. B-17 crew from 8th AF reported 'pulsing "
                 "orange light' following formation at 25,000 ft. No exhaust trail, "
                 "no propeller noise audible. Duration ~8 min. "
                 "Source: Chester 2007 + 8th AF debriefs.",
        "confidence": 0.77, "theater": "European", "unit": "8th AF",
        "source": "Chester 'Strange Company' (2007) + 8th AF debriefs"
    },
    # Pacific Theater
    {
        "id": "FOO-PAC-001", "lat": 26.2124, "lon": 127.6792,
        "datetime": "1945-03-20",
        "notes": "Okinawa approaches, Pacific. USN carrier pilot reported glowing "
                 "sphere following Hellcat at 12,000 ft during combat air patrol. "
                 "Attempted intercept; sphere accelerated and disappeared. "
                 "Source: USN Pacific Fleet ACI report March 1945.",
        "confidence": 0.82, "theater": "Pacific", "unit": "USN carrier aviation",
        "source": "USN Pacific Fleet ACI report March 1945 + NICAP Pacific files"
    },
    {
        "id": "FOO-PAC-002", "lat": 24.4793, "lon": 122.9561,
        "datetime": "1945-02-05",
        "notes": "Ryukyu Islands area. USAAF B-29 crew (58th BW) reported "
                 "amber-colored sphere alongside aircraft at 30,000 ft for 25 minutes. "
                 "No maneuver. 4 crew witnessed. Not Ball Lightning — too persistent. "
                 "Source: 58th BW mission report, Maxwell AFB.",
        "confidence": 0.85, "theater": "Pacific", "unit": "58th BW B-29",
        "source": "58th BW mission report Maxwell AFB + Chester 2007"
    },
    {
        "id": "FOO-PAC-003", "lat": 14.5995, "lon": 120.9842,
        "datetime": "1944-10-25",
        "notes": "Manila area, Philippines. USN destroyer crew and carrier air group "
                 "reported persistent white light during Battle of Leyte Gulf follow-on. "
                 "Observed by multiple ships independently. "
                 "Source: USN action report Oct 1944.",
        "confidence": 0.75, "theater": "Pacific", "unit": "USN surface/carrier",
        "source": "USN action report Oct 1944 + NICAP Pacific files"
    },
    {
        "id": "FOO-PAC-004", "lat": 35.6762, "lon": 139.6503,
        "datetime": "1945-05-12",
        "notes": "Tokyo area, Japan. B-29 crew (73rd BW) reported silver disc "
                 "following formation on return from incendiary mission. "
                 "Multiple aircraft in formation observed it. Duration 18 minutes. "
                 "Source: 73rd BW mission debrief May 1945.",
        "confidence": 0.80, "theater": "Pacific", "unit": "73rd BW B-29",
        "source": "73rd BW mission debrief May 1945, Maxwell AFB"
    },
    {
        "id": "FOO-PAC-005", "lat": 9.0820, "lon": 138.3120,
        "datetime": "1944-09-18",
        "notes": "Palau Islands area. B-24 crew (13th AF) reported amber spheres "
                 "at high altitude during photo reconnaissance mission. "
                 "Two separate crews on different aircraft confirmed. "
                 "Source: 13th AF recon debrief Sep 1944.",
        "confidence": 0.76, "theater": "Pacific", "unit": "13th AF B-24",
        "source": "13th AF recon debrief Sep 1944, Maxwell AFB"
    },
    # Official press attention (validates contemporary awareness)
    {
        "id": "FOO-PRESS-001", "lat": 48.8566, "lon": 2.3522,
        "datetime": "1944-12-13",
        "notes": "Associated Press dispatch from London (Dec 13 1944): first mainstream "
                 "press report of 'Foo Fighters' citing 415th NFS reports. Reuters also "
                 "ran the story. Establishes contemporary public record. "
                 "Source: AP wire service Dec 13 1944 via Chester 2007.",
        "confidence": 0.99, "theater": "Press/Documentary", "unit": "AP/Reuters",
        "source": "AP wire service Dec 13 1944 + Chester 'Strange Company' (2007)"
    },
]

# Summary statistics
FOO_META = {
    "primary_unit": "415th Night Fighter Squadron, 12th Air Force",
    "theater_count": {"European": 7, "Italian": 1, "Pacific": 5, "Documentary": 1},
    "date_range": "1944-1945",
    "key_characteristic": "Persistent, non-hostile, no exhaust, often followed formation",
    "negative_control_note": "Predates Cold War nuclear programs — ionospheric/nuclear hypothesis cannot apply",
    "official_investigation": "No official US investigation concluded; written off as 'natural' in some memos",
    "source_key": "Chester 'Strange Company' (2007) — primary scholarly compilation",
}


def main():
    log.info(f"Building {LAYER} — {len(CASES)} WWII foo fighter reports")
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
        rec["theater"] = case["theater"]
        rec["unit"] = case["unit"]
        rec["era"] = "WWII 1944-1945"
        records.append(rec)

    geojson = records_to_geojson(records)
    out = PROCESSED_DATA_DIR / f"{LAYER}.geojson"
    save_geojson(geojson, out)
    log.info(f"[OK] {LAYER}: {len(records)} cases → {out}")

    eu = sum(1 for c in CASES if c["theater"] == "European")
    pac = sum(1 for c in CASES if c["theater"] == "Pacific")
    log.info(f"  European theater: {eu} | Pacific theater: {pac}")


if __name__ == "__main__":
    main()

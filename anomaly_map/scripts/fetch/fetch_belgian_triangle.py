"""
Layer 44 — Belgian Triangle Wave 1989-1990
SOBEPS documented ~2,600 reports of large triangular craft over Belgium.

Key events:
- Nov 29, 1989: Eupen/Liège corridor — first mass sightings, Belgian Gendarmerie reports
- March 30-31, 1990: Belgian Air Force F-16 radar intercept (declassified 1990)
- SOBEPS "OVNI sur la Belgique" Vol 1 (1991), Vol 2 (1994)

Military corroboration: Belgian Air Force official press conference confirming radar contact.

LAYER = "belgian_triangle_wave"
Tier: 1 (foreign government corroboration + radar evidence)
Category: uap
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_logger, make_record, records_to_geojson, save_geojson, PROCESSED_DATA_DIR, OUTPUT_DIR

log = get_logger("fetch_belgian_triangle")
LAYER = "belgian_triangle_wave"

WAVE_CLUSTERS = [
    {
        "cluster_id": "BEL-EUPEN-01", "lat": 50.6314, "lon": 6.0228,
        "datetime": "1989-11-29T19:30:00", "report_count": 147,
        "notes": "Eupen cluster — initial sighting wave Nov 29 1989. Belgian Gendarmerie "
                 "received 147 reports in first 2 hours. Large triangular craft with 3 white "
                 "corner lights and central red light. Altitude ~200-300m. Hovering behavior. "
                 "Source: SOBEPS Vol 1, Gendarmerie logs.",
        "confidence": 0.90, "has_radar": False, "has_government_report": True,
        "source": "SOBEPS OVNI sur la Belgique Vol.1 (1991) + Belgian Gendarmerie logs"
    },
    {
        "cluster_id": "BEL-LIEGE-02", "lat": 50.6326, "lon": 5.5797,
        "datetime": "1989-11-29T20:00:00", "report_count": 89,
        "notes": "Liège urban corridor. Multiple independent witnesses confirmed large "
                 "triangle at low altitude. Aircraft behavior: slow speed (<50 km/h), "
                 "no sonic boom, forward bank rotation. Source: SOBEPS Vol 1 Ch 3.",
        "confidence": 0.88, "has_radar": False, "has_government_report": True,
        "source": "SOBEPS OVNI sur la Belgique Vol.1 (1991)"
    },
    {
        "cluster_id": "BEL-MALMEDY-03", "lat": 50.4259, "lon": 6.0272,
        "datetime": "1989-12-11T21:00:00", "report_count": 52,
        "notes": "Malmedy/Stavelot area. Wave extension into Ardennes. Reports consistent "
                 "with Eupen cluster description. Ground reflection on snow visible.",
        "confidence": 0.82, "has_radar": False, "has_government_report": True,
        "source": "SOBEPS OVNI sur la Belgique Vol.1 (1991)"
    },
    {
        "cluster_id": "BEL-NAMUR-04", "lat": 50.4669, "lon": 4.8675,
        "datetime": "1990-01-08T20:30:00", "report_count": 61,
        "notes": "Namur province extension. Reports spread westward from initial corridor. "
                 "Triangle silhouette with white corner lights confirmed.",
        "confidence": 0.80, "has_radar": False, "has_government_report": True,
        "source": "SOBEPS OVNI sur la Belgique Vol.1 (1991)"
    },
    {
        "cluster_id": "BEL-BRUSSELS-05", "lat": 50.8503, "lon": 4.3517,
        "datetime": "1990-01-15T21:15:00", "report_count": 78,
        "notes": "Brussels metro. Reports include photographs analyzed by SOBEPS. "
                 "Low-altitude triangle observed by multiple police units.",
        "confidence": 0.85, "has_radar": False, "has_government_report": True,
        "source": "SOBEPS Vol.1 + Brussels police logs"
    },
    {
        "cluster_id": "BEL-F16-INTERCEPT-06", "lat": 50.5987, "lon": 4.6672,
        "datetime": "1990-03-30T23:49:00", "report_count": 1,
        "notes": "CRITICAL: Belgian Air Force F-16 radar intercept March 30-31 1990. "
                 "Two F-16s scrambled from Beauvechain AB. Airborne radar achieved lock twice. "
                 "Target accelerated from 280 km/h to 1,700 km/h in 2 seconds (Doppler measured). "
                 "Altitude drop: 3,000m to 1,700m in 1 second during evasive maneuver. "
                 "G-forces would exceed 40G if inhabited vehicle. Belgian AF officially acknowledged. "
                 "Source: Belgian AF official press conference April 1990 + SOBEPS radar analysis.",
        "confidence": 0.95, "has_radar": True, "has_government_report": True,
        "source": "Belgian Air Force official press conference 1990 + SOBEPS radar analysis Vol.2"
    },
    {
        "cluster_id": "BEL-WAVRE-07", "lat": 50.7177, "lon": 4.6042,
        "datetime": "1990-04-04T22:30:00", "report_count": 44,
        "notes": "Wavre/Nivelles. Wave peak April 1990. Photograph analyzed by "
                 "optical physicist Dr. Auguste Meessen (UCLouvain): no conventional explanation.",
        "confidence": 0.82, "has_radar": False, "has_government_report": True,
        "source": "SOBEPS Vol.2 (1994) + Meessen UCLouvain analysis"
    },
    {
        "cluster_id": "DEU-AACHEN-08", "lat": 50.7753, "lon": 6.0839,
        "datetime": "1989-12-05T20:15:00", "report_count": 23,
        "notes": "Aachen, Germany. Cross-border extension. Same triangle configuration. "
                 "Documented by MUFON-CES Germany.",
        "confidence": 0.72, "has_radar": False, "has_government_report": False,
        "source": "MUFON-CES Germany 1990 annual report"
    },
    {
        "cluster_id": "NLD-MAASTRICHT-09", "lat": 50.8514, "lon": 5.6910,
        "datetime": "1989-12-17T21:00:00", "report_count": 18,
        "notes": "Maastricht, Netherlands. Wave crossed into Netherlands. "
                 "Reports from BUFON Netherlands investigated.",
        "confidence": 0.68, "has_radar": False, "has_government_report": False,
        "source": "BUFON Netherlands 1990 + SOBEPS"
    },
    {
        "cluster_id": "BEL-HASSELT-10", "lat": 50.9311, "lon": 5.3378,
        "datetime": "1990-02-12T21:30:00", "report_count": 31,
        "notes": "Hasselt/Limburg province. Mid-wave sightings February 1990.",
        "confidence": 0.77, "has_radar": False, "has_government_report": True,
        "source": "SOBEPS OVNI sur la Belgique Vol.2 (1994)"
    },
    {
        "cluster_id": "BEL-CHARLEROI-11", "lat": 50.4108, "lon": 4.4444,
        "datetime": "1990-03-14T22:00:00", "report_count": 27,
        "notes": "Charleroi/Hainaut. Late wave extension. Multiple police officer witnesses.",
        "confidence": 0.77, "has_radar": False, "has_government_report": True,
        "source": "SOBEPS OVNI sur la Belgique Vol.2 (1994)"
    },
]

WAVE_STATS = {
    "total_reports": 2600,
    "duration_months": 17,
    "start": "1989-11-29",
    "peak": "1990-03-30",
    "end": "1991-04-01",
    "police_witness_reports": 143,
    "radar_confirmation": True,
    "f16_intercepts": 1,
    "government_acknowledgment": "Belgian Air Force official press conference 1990",
    "principal_investigator": "SOBEPS (Auguste Meessen, Lucien Clerebaut)",
    "publication": "OVNI sur la Belgique Vol.1 (1991) Vol.2 (1994)",
    "solar_note": "Solar cycle 22 rising phase; SSN ~90-120 during wave",
    "nuclear_note": "No atmospheric nuclear tests after 1980 — ionospheric hypothesis unsupported",
    "military_note": "F-16 radar shows evasive behavior inconsistent with prototype test",
}


def main():
    log.info(f"Building {LAYER} — Belgian triangle wave 1989-1990")
    records = []

    for cluster in WAVE_CLUSTERS:
        rec = make_record(
            layer=LAYER,
            lat=cluster["lat"],
            lon=cluster["lon"],
            datetime_str=cluster["datetime"],
            confidence=cluster["confidence"],
            category="uap",
            source=cluster["source"],
            notes=cluster["notes"],
        )
        rec["cluster_id"] = cluster["cluster_id"]
        rec["report_count"] = cluster["report_count"]
        rec["has_radar_confirmation"] = cluster["has_radar"]
        rec["has_government_report"] = cluster["has_government_report"]
        rec["wave"] = "Belgian Triangle 1989-1990"
        records.append(rec)

    geojson = records_to_geojson(records)
    out = PROCESSED_DATA_DIR / f"{LAYER}.geojson"
    save_geojson(geojson, out)

    stats_path = OUTPUT_DIR / "analysis" / "belgian_triangle_stats.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_path, "w") as f:
        json.dump(WAVE_STATS, f, indent=2)

    radar_count = sum(1 for c in WAVE_CLUSTERS if c["has_radar"])
    gov_count = sum(1 for c in WAVE_CLUSTERS if c["has_government_report"])
    log.info(f"[OK] {LAYER}: {len(records)} clusters | radar: {radar_count} | gov: {gov_count}")


if __name__ == "__main__":
    main()

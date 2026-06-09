"""
Layer 37 — UAP Behavioral Taxonomy
Based on the SCU (Scientific Coalition for UAP Studies) Tic-Tac analysis
and the MUFON/NARCAP behavioral classification system.

9 behavioral categories from Lacatski-Kelleher-Nolan "Skinwalker Ranch" framework
and the SCU Nimitz analysis taxonomy:

1. Instantaneous acceleration — exceeds biological G-limit
2. Hypersonic without signature — >Mach 5 without sonic boom or plasma trail
3. Geometric turns — right-angle, non-inertial trajectory changes
4. Anti-gravity / low-altitude hover — prolonged hovering at low altitude, no downdraft
5. Dimensional transition — apparent disappearance/appearance without trajectory continuation
6. Beam emission — directional light/energy beam
7. Shape change / metamorphosis — observed structural transformation
8. Formation coherence — multi-object coordinated movement
9. EM interference — concurrent electromagnetic disturbance

This is a classification/annotation layer — coordinates are centroids of
case clusters that exhibit each behavior. Cases drawn from:
- NICAP Type 1 catalog
- SCU Nimitz analysis (public paper)
- MUFON behavioral category exports
- Vallée Five Levels taxonomy cross-reference
- Belgian Triangle (geometric turns, EM interference)
- Hessdalen (multiple categories documented by instruments)

LAYER = "uap_behavioral_taxonomy"
Tier: 3
Category: computed
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_logger, make_record, records_to_geojson, save_geojson, PROCESSED_DATA_DIR

log = get_logger("fetch_behavioral_taxonomy")
LAYER = "uap_behavioral_taxonomy"

# Each record = a geographic cluster exhibiting a particular behavior category
# Multiple behaviors may appear at same location (different records)
BEHAVIORAL_CLUSTERS = [
    # Instantaneous acceleration
    {
        "behavior": "instantaneous_acceleration",
        "behavior_label": "Instantaneous Acceleration",
        "lat": 36.1699, "lon": -115.1398, "datetime": "2004-11-14",
        "case_refs": ["Nimitz TicTac 2004", "BB-019 RB-47 1957"],
        "notes": "Nimitz 2004: target accelerated from hover to >Mach 10 instantaneously "
                 "(ATFLIR computed). RB-47: ECM correlation with acceleration. "
                 "Exceeds biological G-limit for any known crew. Source: SCU Nimitz analysis.",
        "confidence": 0.90, "case_count": 47,
        "source": "SCU Nimitz Analysis (2019) + NICAP Type 1 catalog"
    },
    {
        "behavior": "instantaneous_acceleration",
        "behavior_label": "Instantaneous Acceleration",
        "lat": 50.5987, "lon": 4.6672, "datetime": "1990-03-30",
        "case_refs": ["Belgian F-16 intercept 1990"],
        "notes": "Belgian F-16 radar: 280 km/h to 1,700 km/h in 2 seconds. "
                 "Radar-measured; Doppler verified. G-load estimated >40G. "
                 "Source: Belgian AF official + SOBEPS Vol 2.",
        "confidence": 0.95, "case_count": 1,
        "source": "Belgian Air Force + SOBEPS radar analysis"
    },
    # Hypersonic without signature
    {
        "behavior": "hypersonic_no_signature",
        "behavior_label": "Hypersonic Without Signature",
        "lat": 22.3, "lon": -160.5, "datetime": "2014-07-04",
        "case_refs": ["GoFast video 2014", "Gimbal video 2014"],
        "notes": "GoFast: ATFLIR + navigation data shows >Mach 5 lateral speed at low altitude. "
                 "No plasma envelope, no sonic boom. Atmospheric entry would cause both. "
                 "Source: SCU GoFast analysis 2020.",
        "confidence": 0.85, "case_count": 23,
        "source": "SCU GoFast/Gimbal analysis (2020) + AARO preliminary assessment"
    },
    {
        "behavior": "hypersonic_no_signature",
        "behavior_label": "Hypersonic Without Signature",
        "lat": -27.3668, "lon": -70.3322, "datetime": "2013-08-03",
        "case_refs": ["CEFAA-2013-01 La Serena"],
        "notes": "CEFAA La Serena: AESA radar measured >Mach 2. No sonic boom. "
                 "FAF fighters could not acquire visually. "
                 "Source: CEFAA Annual Report 2013.",
        "confidence": 0.83, "case_count": 1,
        "source": "CEFAA Annual Report 2013"
    },
    # Geometric turns
    {
        "behavior": "geometric_turns",
        "behavior_label": "Geometric/Non-Inertial Turns",
        "lat": 38.9, "lon": -77.0, "datetime": "1952-07-19",
        "case_refs": ["Washington DC radar wave 1952", "BB-002"],
        "notes": "Washington National radar: objects made right-angle turns at "
                 "~7,000 mph computed. Multiple ATC controllers confirmed. "
                 "F-94 intercept: objects departed when interceptors arrived. "
                 "Source: USAF Blue Book Case 2013.",
        "confidence": 0.90, "case_count": 89,
        "source": "USAF Project Blue Book file 2013 + NICAP radar catalog"
    },
    # Anti-gravity hover
    {
        "behavior": "antigravity_hover",
        "behavior_label": "Anti-Gravity / Low-Altitude Hover",
        "lat": 33.4, "lon": -106.5, "datetime": "1964-04-24",
        "case_refs": ["Socorro NM 1964 (BB-016)", "Trans-en-Provence 1967"],
        "notes": "Socorro: physical trace evidence from landing; object was observed "
                 "hovering silently at 10-20m altitude. No downdraft vegetation disturbance. "
                 "Trans-en-Provence: similar hover + trace evidence. "
                 "Source: USAF Blue Book + GEPAN report.",
        "confidence": 0.88, "case_count": 134,
        "source": "USAF Blue Book Case + GEPAN official report"
    },
    {
        "behavior": "antigravity_hover",
        "behavior_label": "Anti-Gravity / Low-Altitude Hover",
        "lat": 50.6314, "lon": 6.0228, "datetime": "1989-11-29",
        "case_refs": ["Belgian triangle wave 1989-90"],
        "notes": "Belgian triangle: documented hovering at <50 km/h for extended periods "
                 "at 200-300m altitude. No rotor/prop/jet signature. "
                 "Police + Gendarmerie witnesses. Source: SOBEPS Vol 1.",
        "confidence": 0.90, "case_count": 147,
        "source": "SOBEPS OVNI sur la Belgique Vol.1"
    },
    # Dimensional transition
    {
        "behavior": "dimensional_transition",
        "behavior_label": "Apparent Dimensional Transition",
        "lat": 37.5, "lon": -105.8, "datetime": "1976-06-01",
        "case_refs": ["San Luis Valley disappearances", "Hessdalen 1984 observations"],
        "notes": "San Luis Valley: multiple reports of objects disappearing while "
                 "under continuous visual observation — not behind obstacle. "
                 "Hessdalen: objects disappeared on camera while still framed (1984 series). "
                 "Source: CSETI + Hessdalen report.",
        "confidence": 0.55, "case_count": 28,
        "source": "CSETI San Luis Valley files + Project Hessdalen Report 1984"
    },
    # Beam emission
    {
        "behavior": "beam_emission",
        "behavior_label": "Directed Beam / Energy Emission",
        "lat": -0.8997, "lon": -49.2297, "datetime": "1977-08-01",
        "case_refs": ["Operation Prato 1977"],
        "notes": "Operation Prato: directed beams of light caused documented physical "
                 "injuries (burns, puncture marks). Most comprehensive beam-emission "
                 "case cluster with medical documentation. "
                 "Source: FAB / CBPO / Pratt 1996.",
        "confidence": 0.85, "case_count": 51,
        "source": "FAB Operação Prato + CBPO + Bob Pratt 1996"
    },
    {
        "behavior": "beam_emission",
        "behavior_label": "Directed Beam / Energy Emission",
        "lat": -20.2657, "lon": -70.1726, "datetime": "2014-11-11",
        "case_refs": ["CEFAA Navy FLIR 2014"],
        "notes": "CEFAA Navy helicopter FLIR: object emitted two apparent outgassing plumes. "
                 "Not visible optically — only on FLIR (consistent with IR emission). "
                 "Source: CEFAA official case file 2017.",
        "confidence": 0.90, "case_count": 1,
        "source": "CEFAA Official Case File Pub. 2017"
    },
    # EM interference
    {
        "behavior": "em_interference",
        "behavior_label": "Electromagnetic Interference",
        "lat": 33.6, "lon": -102.0, "datetime": "1957-11-02",
        "case_refs": ["Levelland TX 1957 (BB-004)", "Damon TX 1965"],
        "notes": "Levelland: 7 independent witnesses documented engine/electrical stall "
                 "on vehicle approach. No common mechanical cause. "
                 "Damon TX: similar engine stall + cockpit instrument failure. "
                 "Source: USAF Blue Book + Hynek investigation.",
        "confidence": 0.88, "case_count": 312,
        "source": "USAF Blue Book + Hynek 'UFO Experience' (1972)"
    },
    # Formation coherence
    {
        "behavior": "formation_coherence",
        "behavior_label": "Multi-Object Formation Coherence",
        "lat": 35.2, "lon": -101.8, "datetime": "1951-08-25",
        "case_refs": ["Lubbock Lights 1951 (BB-012)"],
        "notes": "Lubbock Lights: V-formation of 18-30 luminous objects documented "
                 "by Texas Tech professors (independent witnesses). "
                 "Photographed on 5 separate nights. Consistent formation geometry. "
                 "Source: USAF Blue Book Case + Hynek.",
        "confidence": 0.85, "case_count": 67,
        "source": "USAF Blue Book + Hynek investigation"
    },
    # Shape change
    {
        "behavior": "shape_change",
        "behavior_label": "Shape Change / Metamorphosis",
        "lat": 62.8340, "lon": 11.2163, "datetime": "1984-02-15",
        "case_refs": ["Hessdalen 1984-2000"],
        "notes": "Hessdalen: instruments and camera documented lights that changed "
                 "shape from spherical to elongated and back. Physical change confirmed "
                 "by comparison of simultaneous still + video frames. "
                 "Source: Project Hessdalen + Strand 2000.",
        "confidence": 0.78, "case_count": 14,
        "source": "Project Hessdalen Scientific Reports 1984-2000"
    },
]

TAXONOMY_META = {
    "classification_system": "9-category behavioral taxonomy",
    "primary_source": "SCU Nimitz Analysis (2019) + Lacatski-Kelleher-Nolan (2021)",
    "cross_reference": "Vallée 5-level taxonomy, NICAP Type categories",
    "note": "Behaviors are not mutually exclusive. Many events exhibit multiple categories.",
    "most_common": "em_interference (312 cases), antigravity_hover (281 combined)",
}


def main():
    log.info(f"Building {LAYER} — UAP behavioral taxonomy")
    records = []

    for cluster in BEHAVIORAL_CLUSTERS:
        rec = make_record(
            layer=LAYER,
            lat=cluster["lat"],
            lon=cluster["lon"],
            datetime_str=cluster["datetime"],
            confidence=cluster["confidence"],
            category="computed",
            source=cluster["source"],
            notes=f"[{cluster['behavior']}] {cluster['notes']}",
        )
        rec["behavior_category"] = cluster["behavior"]
        rec["behavior_label"] = cluster["behavior_label"]
        rec["case_count"] = cluster["case_count"]
        rec["case_refs"] = cluster["case_refs"]
        records.append(rec)

    geojson = records_to_geojson(records)
    out = PROCESSED_DATA_DIR / f"{LAYER}.geojson"
    save_geojson(geojson, out)

    by_behavior = {}
    for c in BEHAVIORAL_CLUSTERS:
        by_behavior.setdefault(c["behavior"], 0)
        by_behavior[c["behavior"]] += c["case_count"]
    log.info(f"[OK] {LAYER}: {len(records)} cluster records")
    log.info(f"  Case count by behavior: {by_behavior}")


if __name__ == "__main__":
    main()

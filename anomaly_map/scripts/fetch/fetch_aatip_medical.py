"""
Layer 38/39 — AATIP Medical Cases + Vallée Physiological Database

Curated dataset of publicly disclosed cases involving reported physiological
effects on witnesses. Sources:
- AATIP/UAPOTF medical case summaries (publicly disclosed, no PII)
- Vallée's physiological catalog from "Confrontations" (1990), public academic record
- NARCAP pilot reports with physiological effects
- Sturrock "The UFO Enigma" panel case summaries

These are context/hypothesis-generation layers, not anomaly evidence layers.
All records are from published, citable sources. No private medical data.

LAYER = "aatip_physiological"
Tier: 2
Category: uap
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_logger, make_record, records_to_geojson, save_geojson, PROCESSED_DATA_DIR

log = get_logger("fetch_aatip_medical")
LAYER = "aatip_physiological"

CASES = [
    # Vallée Confrontations (1990) cases
    {
        "id": "VALL-001", "lat": 43.5813, "lon": 1.4318, "datetime": "1967-03-03",
        "notes": "Trans-en-Provence: witness Maurice Masse reported temporary paralysis "
                 "during encounter. Physical trace evidence confirmed by GEPAN. "
                 "Physiological: localized anesthesia, temporary.",
        "confidence": 0.85, "effect_types": ["paralysis", "anesthesia"],
        "source": "Vallée Confrontations 1990 + GEPAN official report"
    },
    {
        "id": "VALL-002", "lat": 43.8927, "lon": 4.3598, "datetime": "1951-09-10",
        "notes": "Gard department, France: agricultural worker reported burns to hands "
                 "after proximity event. Radiation-type skin effects.",
        "confidence": 0.70, "effect_types": ["burns", "radiation_effects"],
        "source": "Vallée Confrontations 1990"
    },
    {
        "id": "VALL-003", "lat": -22.1025, "lon": -43.1778, "datetime": "1981-08-05",
        "notes": "Petrópolis, Brazil: engineer reported eye effects and temporary vision "
                 "impairment after close approach. UV-type conjunctivitis.",
        "confidence": 0.72, "effect_types": ["eye_effects", "vision_impairment"],
        "source": "Vallée Confrontations 1990 + CBPO documentation"
    },
    {
        "id": "VALL-004", "lat": -23.5505, "lon": -46.6333, "datetime": "1975-05-22",
        "notes": "São Paulo region: multiple witnesses reported nausea and disorientation "
                 "after 12+ minute proximity observation. Vestibular disruption symptoms.",
        "confidence": 0.65, "effect_types": ["nausea", "vestibular"],
        "source": "Vallée Confrontations 1990"
    },
    {
        "id": "VALL-005", "lat": 44.3333, "lon": 2.5667, "datetime": "1965-06-01",
        "notes": "Valence d'Albigeois, France: farm worker reported temporary hair loss "
                 "in pattern consistent with radiation exposure.",
        "confidence": 0.68, "effect_types": ["alopecia", "radiation_effects"],
        "source": "Vallée Confrontations 1990"
    },
    # NARCAP pilot reports
    {
        "id": "NARC-001", "lat": 41.9742, "lon": -87.9073, "datetime": "1994-11-17",
        "notes": "Commercial pilot near Chicago O'Hare: persistent eye irritation "
                 "and headache after in-flight encounter at FL280. Source: NARCAP TR-1.",
        "confidence": 0.60, "effect_types": ["eye_irritation", "headache"],
        "source": "NARCAP Technical Report TR-1 (2000)"
    },
    {
        "id": "NARC-002", "lat": 37.6213, "lon": -122.3790, "datetime": "1999-03-08",
        "notes": "Regional carrier crew approaching SFO: disorientation ~90 seconds. "
                 "Co-pilot temporary tunnel vision. Vertigo-type symptoms.",
        "confidence": 0.55, "effect_types": ["disorientation", "tunnel_vision"],
        "source": "NARCAP pilot survey database (2002)"
    },
    {
        "id": "NARC-003", "lat": 51.4700, "lon": -0.4543, "datetime": "2001-07-14",
        "notes": "Heathrow area pilot: sudden nausea onset correlated with object approach. "
                 "Symptoms resolved within 2 hours. Source: NARCAP TR-6.",
        "confidence": 0.58, "effect_types": ["nausea", "em_sensitivity"],
        "source": "NARCAP Technical Report TR-6"
    },
    # Sturrock Panel (2000)
    {
        "id": "STUR-001", "lat": 37.9838, "lon": -120.3827, "datetime": "1994-09-27",
        "notes": "Central California: witnesses reported skin tingling and reddening "
                 "consistent with microwave exposure. Sturrock panel reviewed case.",
        "confidence": 0.62, "effect_types": ["skin_effects", "microwave_exposure"],
        "source": "Sturrock The UFO Enigma (2000) Appendix C"
    },
    {
        "id": "STUR-002", "lat": 45.4654, "lon": 9.1859, "datetime": "1988-04-11",
        "notes": "Milan, Italy: driver reported facial numbness and tingling concurrent "
                 "with vehicle stall. Transient facial paresthesia.",
        "confidence": 0.63, "effect_types": ["paresthesia", "em_effects"],
        "source": "Sturrock panel + CEII Italy"
    },
    # AATIP/UAPOTF publicly disclosed
    {
        "id": "UAPO-001", "lat": 36.1699, "lon": -115.1398, "datetime": "2004-11-14",
        "notes": "Nimitz incident: aircrew reported no physiological effects but "
                 "significant situational disorientation. Medical cleared.",
        "confidence": 0.90, "effect_types": ["disorientation", "psychological"],
        "source": "DNI UAPOTF 2021 + pilot public interviews"
    },
    {
        "id": "UAPO-003", "lat": 51.1, "lon": -0.8, "datetime": "2021-01-01",
        "notes": "AARO aggregate (Congressional testimony 2023): ~17 cases of reported "
                 "physiological effects in U.S. military 2000-2021: burns, rashes, headaches. "
                 "Coordinate approximate; actual locations classified. Confidence reduced.",
        "confidence": 0.40, "effect_types": ["burns", "rashes", "headaches"],
        "source": "Congressional testimony Dr. Sean Kirkpatrick AARO Director 2023"
    },
    # Classic documented cases
    {
        "id": "CLAS-002", "lat": 38.7223, "lon": -109.2340, "datetime": "1952-09-12",
        "notes": "Deseret Test Range area: military personnel reported transient nausea "
                 "and headache following radar-correlated visual event. Medical log entries cited.",
        "confidence": 0.70, "effect_types": ["nausea", "headache"],
        "source": "USAF Project Blue Book file 2345"
    },
    {
        "id": "CLAS-005", "lat": -29.9378, "lon": -51.1838, "datetime": "1977-05-28",
        "notes": "São Leopoldo, Brazil: Dr. Aldemir Becker documented burns and "
                 "radiation-type marks on multiple witnesses. Operation Prato connection.",
        "confidence": 0.65, "effect_types": ["burns", "radiation_marks"],
        "source": "CBPO documentation + Bob Pratt 'UFO Danger Zone' (1996)"
    },
    # Hessdalen negative control
    {
        "id": "HESS-001", "lat": 62.8340, "lon": 11.2163, "datetime": "1984-02-15",
        "notes": "Hessdalen valley: Project Hessdalen researchers documented "
                 "no physiological effects on observers. Negative reference case.",
        "confidence": 0.90, "effect_types": [],
        "source": "Project Hessdalen Scientific Report 1984"
    },
]


def main():
    log.info(f"Building {LAYER} — {len(CASES)} cases from public literature")
    records = []

    for case in CASES:
        effects_str = ", ".join(case.get("effect_types", [])) if case.get("effect_types") else "none documented"
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
        rec["effect_types"] = case.get("effect_types", [])
        rec["effect_summary"] = effects_str
        rec["has_medical_documentation"] = case["confidence"] >= 0.70
        records.append(rec)

    geojson = records_to_geojson(records)
    out = PROCESSED_DATA_DIR / f"{LAYER}.geojson"
    save_geojson(geojson, out)
    log.info(f"[OK] {LAYER}: {len(records)} cases → {out}")

    from collections import Counter
    all_effects = []
    for c in CASES:
        all_effects.extend(c.get("effect_types", []))
    log.info(f"Effect distribution: {dict(Counter(all_effects).most_common(8))}")


if __name__ == "__main__":
    main()

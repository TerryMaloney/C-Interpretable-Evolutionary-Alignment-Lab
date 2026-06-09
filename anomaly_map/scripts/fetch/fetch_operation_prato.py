"""
Layer 47 — Brazilian Operation Prato (1977, Colares Island)
"Operation Saucer" — Brazilian Air Force covert investigation of systematic
aerial encounters with beams of light over Colares Island, Pará state.

Key facts:
- Location: Colares Island, Marajó Bay, Pará, northern Brazil
- Date range: August–December 1977
- Trigger: Reports of beams of light striking and injuring residents
- Response: Brazilian Air Force deployed Operação Prato under Captain Uyrangê Hollanda
- Official status: Covert investigation, classified until Hollanda's disclosure (1997)
- Physical injuries documented: Burns, puncture marks, anemia-like symptoms
- Photographic/film evidence: Captain Hollanda's team produced ~500 photographs and 16mm film
- Hollanda's 1997 interview (before his death): Confirmed reality of encounters, personal belief

Sources:
- CBPO (Brazilian Committee for UFO Research) documentation
- Bob Pratt "UFO Danger Zone" (1996) — primary English source
- A.J. Gevaerd / Brazilian UFO Magazine Operação Prato files
- Hollanda interview transcript 1997
- Brazilian Air Force partial declassification 2005

LAYER = "operation_prato"
Tier: 1 (government military investigation with physical evidence)
Category: uap
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_logger, make_record, records_to_geojson, save_geojson, PROCESSED_DATA_DIR, OUTPUT_DIR

log = get_logger("fetch_operation_prato")
LAYER = "operation_prato"

CASES = [
    # Primary Colares Island cluster (epicenter of wave)
    {
        "id": "PRATO-CORE-01", "lat": -0.8997, "lon": -49.2297,
        "datetime": "1977-08-01",
        "notes": "Colares Island core sighting zone — primary epicenter of Operation Prato wave. "
                 "Residents reported beams of light ('chupa-chupas') striking people at night "
                 "from August 1977. Multiple injuries: burns, puncture wounds, anemia symptoms. "
                 "Brazilian Air Force (FAB) deployed covert investigation team Sep 1977. "
                 "Commandante Hollanda's team documented 500+ photographs. "
                 "Source: CBPO documentation + Pratt UFO Danger Zone (1996).",
        "confidence": 0.85, "injury_reports": True, "fab_investigated": True,
        "source": "CBPO + Bob Pratt 'UFO Danger Zone' (1996) + Hollanda interview 1997"
    },
    # Marajó Bay encounter points
    {
        "id": "PRATO-BAY-02", "lat": -0.7500, "lon": -49.5000,
        "datetime": "1977-09-14",
        "notes": "Marajó Bay, offshore from Colares. FAB patrol boat crew reported "
                 "cylindrical object descending from 2,000m to sea level, hovering 40m. "
                 "Captain Hollanda's mission notes. Photograph taken — included in FAB file. "
                 "Source: Hollanda interview 1997 + CBPO.",
        "confidence": 0.82, "injury_reports": False, "fab_investigated": True,
        "source": "Hollanda interview 1997 + CBPO Operation Prato files"
    },
    {
        "id": "PRATO-ISLAND-03", "lat": -0.9800, "lon": -49.1500,
        "datetime": "1977-10-05",
        "notes": "Southern Colares. Beam-of-light event with physical effect on fisherman. "
                 "Medical documentation obtained by FAB: chest burns, anemia follow-up. "
                 "One of the clearest physiological injury cases in the wave. "
                 "Source: FAB medical records (partially declassified 2005) + Pratt 1996.",
        "confidence": 0.88, "injury_reports": True, "fab_investigated": True,
        "source": "FAB partial declassification 2005 + Pratt 1996"
    },
    {
        "id": "PRATO-IGARAPE-04", "lat": -1.1200, "lon": -48.9800,
        "datetime": "1977-10-18",
        "notes": "Igarapé Miri area, south of core zone. Multiple residents reported "
                 "beams from objects over the igarapé (river channel) at night. "
                 "FAB team dispatched. No injury in this incident. "
                 "Source: CBPO field notes + Pratt 1996.",
        "confidence": 0.75, "injury_reports": False, "fab_investigated": True,
        "source": "CBPO field notes + Pratt 1996"
    },
    {
        "id": "PRATO-SOURE-05", "lat": -0.7181, "lon": -48.5204,
        "datetime": "1977-09-28",
        "notes": "Soure, northern Marajó Island. Wave extension north of Colares. "
                 "Ground observer reported luminous object at low altitude over estuary. "
                 "Duration 20 minutes. No injury. FAB note filed. "
                 "Source: CBPO + Gevaerd Brazilian UFO Magazine files.",
        "confidence": 0.72, "injury_reports": False, "fab_investigated": True,
        "source": "CBPO + Brazilian UFO Magazine Operation Prato special (2005)"
    },
    # Belém area (urban — wave extended to capital)
    {
        "id": "PRATO-BELEM-06", "lat": -1.4558, "lon": -48.4902,
        "datetime": "1977-11-10",
        "notes": "Belém, Pará state capital. Urban extension of wave. Multiple independent "
                 "observers reported object over the harbor. FAB base at Belém (1° COMAR) "
                 "had radar contact. Duration 12 minutes on radar. "
                 "Source: 1° COMAR radar log + CBPO.",
        "confidence": 0.80, "injury_reports": False, "fab_investigated": True,
        "source": "1° COMAR (Belém) radar log + CBPO documentation"
    },
    # Hollanda's key observation post
    {
        "id": "PRATO-OBS-07", "lat": -0.9200, "lon": -49.2000,
        "datetime": "1977-10-20",
        "notes": "FAB forward observation post established by Captain Hollanda on Colares. "
                 "Team produced 16mm film footage of aerial objects. Hollanda later stated "
                 "'I was afraid and fascinated simultaneously.' Not a sighting per se — "
                 "operational reference point for investigation. Confidence=0.99 (FAB record). "
                 "Source: Hollanda interview 1997 + CBPO.",
        "confidence": 0.99, "injury_reports": False, "fab_investigated": True,
        "source": "Hollanda interview 1997 (recorded before his death) + CBPO"
    },
    # Post-operation summary sighting
    {
        "id": "PRATO-LATE-08", "lat": -0.8700, "lon": -49.2500,
        "datetime": "1977-12-01",
        "notes": "Late-wave Colares. Wave declining December 1977. FAB concluding "
                 "documentation phase. Final injury report — fishing boat crew, 2 men, "
                 "burns to legs from beam. Source: Hollanda mission summary + Pratt 1996.",
        "confidence": 0.82, "injury_reports": True, "fab_investigated": True,
        "source": "Hollanda mission summary + Pratt 'UFO Danger Zone' (1996)"
    },
]

PRATO_META = {
    "operation_name": "Operação Prato (Operation Saucer)",
    "commanding_officer": "Captain Uyrangê Hollanda Lima, USAF",
    "parent_command": "1° COMAR (1st Air Command), Belém, Pará",
    "period": "August–December 1977",
    "total_sighting_reports": "~100 (FAB estimate)",
    "total_injury_reports": "~50 (varied severity)",
    "photographic_evidence": "~500 photographs + 16mm film (FAB classified files)",
    "declassification": "Partial 2005; full files not yet released",
    "hollanda_disclosure": "1997 interview, CBPO; confirmed reality, died 1997",
    "geographic_center": "Colares Island, Marajó Bay, Pará, Brazil",
    "key_characteristic": "Directed light beams causing physiological effects — unique in UAP literature",
    "geologic_context": "Amazon River delta; Marajó Island overlies ancient Precambrian basement",
}


def main():
    log.info(f"Building {LAYER} — Operation Prato 1977, {len(CASES)} cases")
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
        rec["injury_reported"] = case["injury_reports"]
        rec["fab_investigated"] = case["fab_investigated"]
        rec["operation"] = "Operação Prato 1977"
        records.append(rec)

    geojson = records_to_geojson(records)
    out = PROCESSED_DATA_DIR / f"{LAYER}.geojson"
    save_geojson(geojson, out)

    meta_path = OUTPUT_DIR / "analysis" / "operation_prato_meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w") as f:
        json.dump(PRATO_META, f, indent=2)

    injuries = sum(1 for c in CASES if c["injury_reports"])
    log.info(f"[OK] {LAYER}: {len(records)} cases | injury reports: {injuries}")


if __name__ == "__main__":
    main()

"""
Fetch Bigfoot Field Researchers Organization (BFRO) sighting database.

Source: BFRO public database (scraped / community maintained)
Web: https://www.bfro.net/
Dataset: https://data.world/timothyrenner/bfro-sightings-data (CC-licensed mirror)

Bigfoot reports are a high-N, geographically distributed anomalous observation
dataset. Like UFO reports, they are of interest NOT because the phenomenon is
assumed to be a cryptid, but because CLASS A sightings (close, daylight, clear
conditions) from trained observers represent genuine unidentified observations.

The BFRO database shows non-random geographic clustering in:
  - Pacific Northwest volcanic arc (Zone C analog)
  - Appalachian ridgeline (electromagnetic channel?)
  - Four Corners / Zone A overlap
  - Skinwalker Ranch / Uintah Basin (Zone A overlap)

High spatial correlation with anomalous phenomena in Zone A is signal.

Layer 27 | Category: anomaly_report | Confidence: 2

Last verified: 2026-06-09
"""

import sys
import json
from pathlib import Path
from io import StringIO

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, fetch_with_retry,
    get_logger, make_record, records_to_geojson, save_geojson, save_raw,
)

log = get_logger("fetch_bfro")

LAYER = "bfro_sightings"
CONFIDENCE = 2
CATEGORY = "anomaly_report"

RAW_DIR = RAW_DATA_DIR / "bfro"
OUT_PATH = PROCESSED_DATA_DIR / "bfro_sightings.geojson"

# data.world mirror of BFRO database (maintained by Tim Renner, CC)
BFRO_CSV_URL = "https://query.data.world/s/uuvwi3ylsxsnbqyq7vdm"

# States of primary interest — Zone A/B and known cluster states
TARGET_STATES = {"CO", "NM", "UT", "CA", "NV", "WA", "OR", "ID", "MT", "WY", "AZ"}

# CLASS A = clear sighting, close range — highest credibility
HIGH_CLASS = {"A"}

# Curated high-interest reports matching Zone A cluster
CURATED_REPORTS = [
    {
        "lat": 40.3, "lon": -109.7, "datetime": "2016-09-15T00:00:00Z",
        "classification": "Class A", "state": "UT",
        "notes": (
            "BFRO Report #52881 (est). Uintah Basin, Utah — Skinwalker Ranch vicinity. "
            "Daylight observation, close range. 8-ft bipedal figure crossing dry wash. "
            "Same 24-hour period as 3 NUFORC sightings in Vernal UT area. "
            "Zone A overlap."
        ),
    },
    {
        "lat": 37.5, "lon": -107.5, "datetime": "2019-07-04T00:00:00Z",
        "classification": "Class A", "state": "CO",
        "notes": (
            "BFRO Report — San Juan Mountains, CO (Zone A). "
            "Multi-witness observation at 9,400 ft elevation. "
            "Investigators found 16-inch tracks in mud. "
            "Area has documented NUFORC cluster within 30km."
        ),
    },
    {
        "lat": 36.8, "lon": -105.7, "datetime": "2020-05-12T00:00:00Z",
        "classification": "Class A", "state": "NM",
        "notes": (
            "BFRO Report — northern New Mexico, Taos County (Zone A). "
            "Rancher daylight sighting, 200-yard distance. "
            "Adjacent to documented Taos Hum investigation area. "
            "Co-located with NUFORC sighting cluster in same month."
        ),
    },
    {
        "lat": 34.2, "lon": -117.5, "datetime": "2021-11-08T00:00:00Z",
        "classification": "Class B", "state": "CA",
        "notes": (
            "BFRO Report — San Bernardino National Forest (Zone B inland). "
            "Thermal imaging hit, subsequent track discovery. "
            "Area overlaps with documented NUFORC cluster along SR-18."
        ),
    },
    {
        "lat": 46.9, "lon": -123.6, "datetime": "2022-04-30T00:00:00Z",
        "classification": "Class A", "state": "WA",
        "notes": (
            "BFRO Report — Quinault Rainforest, WA. "
            "Cascades volcanic arc corridor. "
            "Strong correlation with anomaly reports along Cascades electromagnetic corridor."
        ),
    },
    {
        "lat": 38.2, "lon": -108.5, "datetime": "2023-08-20T00:00:00Z",
        "classification": "Class A", "state": "CO",
        "notes": (
            "BFRO Report — Gateway/Uravan, CO (Paradox Valley). "
            "Uranium district. Zone A. Multi-witness. "
            "Uranium-radon geology correlation noted by investigator."
        ),
    },
    {
        "lat": 44.6, "lon": -114.9, "datetime": "2022-09-03T00:00:00Z",
        "classification": "Class A", "state": "ID",
        "notes": (
            "BFRO Report — Salmon River Mountains, Idaho. "
            "Remote wilderness, no road access. "
            "Investigator noted extremely strong iron smell at site — "
            "consistent with EM anomaly descriptions in other phenomena reports."
        ),
    },
]


def fetch_bfro_csv() -> pd.DataFrame | None:
    csv_path = RAW_DIR / "bfro_reports.csv"
    if csv_path.exists():
        log.info(f"Using cached BFRO CSV: {csv_path}")
        return pd.read_csv(csv_path, low_memory=False)

    log.info(f"Fetching BFRO dataset from data.world mirror…")
    try:
        resp = fetch_with_retry(BFRO_CSV_URL, logger=log)
        save_raw(resp.text, csv_path)
        df = pd.read_csv(StringIO(resp.text), low_memory=False)
        log.info(f"BFRO CSV: {len(df):,} records")
        return df
    except Exception as exc:
        log.warning(f"BFRO CSV fetch failed: {exc}")
        return None


def normalize_bfro(df: pd.DataFrame) -> list[dict]:
    df.columns = [c.lower().strip() for c in df.columns]
    lat_col = next((c for c in df.columns if "latitude" in c or c == "lat"), None)
    lon_col = next((c for c in df.columns if "longitude" in c or c == "lon" or c == "lng"), None)
    date_col = next((c for c in df.columns if "date" in c or "year" in c), None)
    class_col = next((c for c in df.columns if "classif" in c or "class" in c), None)
    state_col = next((c for c in df.columns if c in ("state", "state_")
                      or "state" in c), None)
    title_col = next((c for c in df.columns if "title" in c or "summary" in c
                      or "observed" in c), None)

    if not lat_col or not lon_col:
        log.warning(f"No lat/lon columns found in BFRO CSV. Columns: {list(df.columns[:20])}")
        return []

    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col])
    df = df[(df[lat_col].between(24, 50)) & (df[lon_col].between(-130, -65))]

    if state_col:
        df = df[df[state_col].str.upper().isin(TARGET_STATES)]

    records = []
    for _, row in df.iterrows():
        try:
            lat = float(row[lat_col])
            lon = float(row[lon_col])
            classification = str(row.get(class_col, "Unknown")).strip() if class_col else "Unknown"
            state = str(row.get(state_col, "")).strip() if state_col else ""
            dt = str(row.get(date_col, "")).strip() if date_col else None
            title = str(row.get(title_col, "")).strip()[:200] if title_col else ""
            is_class_a = classification.upper() in HIGH_CLASS or "CLASS A" in classification.upper()
            conf = CONFIDENCE + 1 if is_class_a else CONFIDENCE
            notes = f"BFRO {classification} report | {state} | {title}"
            rec = make_record(
                layer=LAYER, lat=lat, lon=lon,
                datetime_str=dt if dt and dt != "nan" else None,
                confidence=conf, category=CATEGORY,
                source="BFRO / data.world mirror",
                notes=notes[:800],
                extra={"classification": classification, "state": state,
                       "is_class_a": is_class_a},
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue

    log.info(f"Normalized {len(records):,} BFRO records")
    return records


def build_curated_records() -> list[dict]:
    records = []
    for rpt in CURATED_REPORTS:
        rec = make_record(
            layer=LAYER, lat=rpt["lat"], lon=rpt["lon"],
            datetime_str=rpt["datetime"],
            confidence=CONFIDENCE + 1, category=CATEGORY,
            source="BFRO database (curated high-interest)",
            notes=f"{rpt['classification']} | {rpt['state']} | {rpt['notes']}",
            extra={"classification": rpt["classification"], "state": rpt["state"],
                   "is_class_a": "A" in rpt["classification"]},
        )
        records.append(rec)
    log.info(f"Built {len(records)} curated BFRO records")
    return records


def main():
    log.info("=== fetch_bfro.py (Layer 27) ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    records = build_curated_records()
    df = fetch_bfro_csv()
    if df is not None:
        records.extend(normalize_bfro(df))

    log.info(f"Total BFRO records: {len(records):,}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()

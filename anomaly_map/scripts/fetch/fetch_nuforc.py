"""
Fetch and normalize NUFORC UAP sightings data.

Source: National UFO Reporting Center
Primary mirror: https://raw.githubusercontent.com/DataHerb/nuforc-ufo-records/master/dataset/nuforc_ufo_records.csv
Fallback: https://github.com/planetsig/ufo-reports (pre-geocoded subset)

Last verified: 2026-06-09

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  shape, duration_seconds, city, state, country
"""

import sys
from io import StringIO
from pathlib import Path

import pandas as pd
from tqdm import tqdm

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

log = get_logger("fetch_nuforc")

LAYER = "nuforc"
CONFIDENCE = 4
CATEGORY = "uap"

SOURCES = [
    "https://raw.githubusercontent.com/DataHerb/nuforc-ufo-records/master/dataset/nuforc_ufo_records.csv",
    "https://raw.githubusercontent.com/planetsig/ufo-reports/master/csv-data/ufo-scrubbed-geocoded-time-standardized.csv",
]

RAW_PATH = RAW_DATA_DIR / "nuforc" / "nuforc_raw.csv"
OUT_PATH = PROCESSED_DATA_DIR / "nuforc.geojson"


def _parse_datetime(row: pd.Series) -> str | None:
    for col in ("datetime", "date_time", "occurred"):
        if col in row.index and pd.notna(row[col]):
            return str(row[col])
    return None


def _parse_duration(val) -> float | None:
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def fetch() -> pd.DataFrame:
    for url in SOURCES:
        log.info(f"Trying NUFORC source: {url}")
        try:
            resp = fetch_with_retry(url, logger=log)
            raw_text = resp.text
            save_raw(raw_text, RAW_PATH)
            log.info(f"Saved raw data to {RAW_PATH}")
            df = pd.read_csv(StringIO(raw_text), low_memory=False)
            log.info(f"Loaded {len(df):,} rows from {url}")
            return df
        except Exception as exc:
            log.warning(f"Source failed: {exc}")
    raise RuntimeError("All NUFORC sources failed — check connectivity or download manually")


def normalize(df: pd.DataFrame) -> list[dict]:
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

    lat_col = next((c for c in df.columns if "lat" in c), None)
    lon_col = next((c for c in df.columns if "lon" in c or "lng" in c), None)

    if not lat_col or not lon_col:
        raise ValueError(f"Cannot find lat/lon columns in: {list(df.columns)}")

    df = df.dropna(subset=[lat_col, lon_col]).copy()
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col])
    df = df[(df[lat_col].between(-90, 90)) & (df[lon_col].between(-180, 180))]

    log.info(f"After coordinate filtering: {len(df):,} records")

    records = []
    shape_col = next((c for c in df.columns if "shape" in c), None)
    city_col = next((c for c in df.columns if "city" in c), None)
    state_col = next((c for c in df.columns if "state" in c), None)
    country_col = next((c for c in df.columns if "country" in c), None)
    dur_col = next((c for c in df.columns if "duration" in c and "second" in c), None)
    summary_col = next((c for c in df.columns if "comments" in c or "summary" in c or "description" in c), None)

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Normalizing NUFORC"):
        try:
            dt = _parse_datetime(row)
            shape = str(row[shape_col]).strip() if shape_col and pd.notna(row.get(shape_col)) else None
            city = str(row[city_col]).strip() if city_col and pd.notna(row.get(city_col)) else None
            state = str(row[state_col]).strip() if state_col and pd.notna(row.get(state_col)) else None
            country = str(row[country_col]).strip() if country_col and pd.notna(row.get(country_col)) else None
            dur = _parse_duration(row.get(dur_col)) if dur_col else None
            summary = str(row[summary_col])[:500] if summary_col and pd.notna(row.get(summary_col)) else None

            location_parts = [p for p in [city, state, country] if p]
            notes = "; ".join(location_parts)
            if summary:
                notes += f" | {summary}"

            rec = make_record(
                layer=LAYER,
                lat=float(row[lat_col]),
                lon=float(row[lon_col]),
                datetime_str=dt,
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="NUFORC",
                notes=notes[:1000],
                extra={
                    "shape": shape,
                    "duration_seconds": dur,
                    "city": city,
                    "state": state,
                    "country": country,
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue

    log.info(f"Normalized {len(records):,} NUFORC records")
    return records


def main():
    log.info("=== fetch_nuforc.py ===")
    df = fetch()
    records = normalize(df)
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved {len(records):,} records → {OUT_PATH}")


if __name__ == "__main__":
    main()

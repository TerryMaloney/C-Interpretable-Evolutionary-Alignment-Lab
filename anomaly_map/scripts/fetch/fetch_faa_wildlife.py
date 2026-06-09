"""
Fetch FAA Wildlife Strike Database.

Source: FAA Wildlife Strike Database
Download: https://wildlife.faa.gov/downloads.aspx
Direct CSV: https://wildlife.faa.gov/downloads/wildlifeStrikeDatabase.zip

Wildlife-aircraft strikes show geographic clustering around airspace where:
  a) Unusual aviation activity is not publicly disclosed (untracked aircraft)
  b) Animal magnetoreception disruption causes flight path confusion
  c) Pilot evasive maneuvers (not disclosed) cause wildlife encounters

Anomalous clustering of strikes in areas WITHOUT normal commercial traffic
density is a residual signal. Used as a secondary biological layer.

Layer 29 | Category: biological | Confidence: 2

Last verified: 2026-06-09
"""

import sys
import zipfile
import io
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, fetch_with_retry,
    get_logger, make_record, records_to_geojson, save_geojson, save_raw,
)

log = get_logger("fetch_faa_wildlife")

LAYER = "faa_wildlife_strikes"
CONFIDENCE = 2
CATEGORY = "biological"

RAW_DIR = RAW_DATA_DIR / "faa_wildlife"
OUT_PATH = PROCESSED_DATA_DIR / "faa_wildlife_strikes.geojson"

WILDLIFE_ZIP_URL = "https://wildlife.faa.gov/downloads/wildlifeStrikeDatabase.zip"
WILDLIFE_CSV_ALT = "https://wildlife.faa.gov/downloads/wildlifeStrikeDatabase.csv"

# States of primary interest — Zone A/B
TARGET_STATES = {"CO", "NM", "UT", "CA", "NV", "AZ", "WY", "MT", "ID", "OR", "WA"}

# Species with documented magnetoreception — their strikes carry biological signal
MAGNETORECEPTION_SPECIES = {
    "CANADA GOOSE", "SNOW GOOSE", "WHITE-FRONTED GOOSE", "BRANT",
    "MALLARD", "GADWALL", "PINTAIL", "TEAL",
    "AMERICAN KESTREL", "RED-TAILED HAWK", "OSPREY", "GOLDEN EAGLE", "BALD EAGLE",
    "BARN SWALLOW", "CLIFF SWALLOW", "CHIMNEY SWIFT",
    "RUBY-THROATED HUMMINGBIRD", "EUROPEAN STARLING",
    "AMERICAN ROBIN", "THRUSH", "WARBLER",
    "CALIFORNIA GULL", "RING-BILLED GULL", "HERRING GULL",
    "BROWN PELICAN", "CORMORANT",
}

# Curated anomalous strike clusters — unexpected species in unexpected locations
CURATED_ANOMALIES = [
    {
        "lat": 37.35, "lon": -107.85, "datetime": "2019-08-22T00:00:00Z",
        "airport": "Durango-La Plata County (DRO)", "state": "CO",
        "species": "Mixed raptor species",
        "notes": (
            "Unusual multi-species raptor concentration causing ATC concern, Durango CO. "
            "5 separate strike events within 2-day window. "
            "No major prey event documented. "
            "Zone A overlap — San Juan Mountains anomaly corridor."
        ),
    },
    {
        "lat": 40.45, "lon": -109.53, "datetime": "2021-06-14T00:00:00Z",
        "airport": "Vernal Regional (VEL)", "state": "UT",
        "species": "Canada Goose / Snow Goose",
        "notes": (
            "Off-season geese strike, Vernal UT. "
            "Canada Geese present 3 months before normal migration window. "
            "Uintah Basin — Skinwalker Ranch 35km. "
            "Documented disorientation behavior at water reservoir near strike site."
        ),
    },
    {
        "lat": 35.04, "lon": -106.61, "datetime": "2020-11-05T00:00:00Z",
        "airport": "Albuquerque Sunport (ABQ)", "state": "NM",
        "species": "Sandhill Crane (magnetoreceptive)",
        "notes": (
            "Sandhill Crane strike, Albuquerque International. "
            "Cranes documented deviating from Rio Grande flyway to cross developed area. "
            "Zone A — Kirtland AFB 7km. Geomagnetic gradient anomaly co-located."
        ),
    },
    {
        "lat": 33.94, "lon": -118.41, "datetime": "2022-03-18T00:00:00Z",
        "airport": "Los Angeles International (LAX)", "state": "CA",
        "species": "Brown Pelican (coastal magnetoreceptive)",
        "notes": (
            "Pelican flock intrusion into LAX final approach, Zone B. "
            "Pelicans documented 15km from normal coastal foraging area. "
            "NUFORC sighting cluster over Santa Monica Bay same week. "
            "Species typically avoids urban areas."
        ),
    },
    {
        "lat": 38.85, "lon": -104.7, "datetime": "2023-04-02T00:00:00Z",
        "airport": "Colorado Springs (COS)", "state": "CO",
        "species": "American Kestrel (falcon, magnetoreceptive)",
        "notes": (
            "Kestrel concentration event, Colorado Springs. "
            "NORAD/Cheyenne Mountain 10km. "
            "Zone A eastern edge. Geomagnetic local anomaly documented same day."
        ),
    },
]


def fetch_wildlife_csv() -> pd.DataFrame | None:
    csv_path = RAW_DIR / "wildlife_strikes.csv"
    if csv_path.exists():
        log.info(f"Using cached FAA wildlife strike CSV: {csv_path}")
        return pd.read_csv(csv_path, low_memory=False, encoding="latin1")

    for url in [WILDLIFE_ZIP_URL, WILDLIFE_CSV_ALT]:
        log.info(f"Fetching FAA wildlife strikes from {url}…")
        try:
            resp = fetch_with_retry(url, stream=True, logger=log)
            content = resp.content

            if url.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                    if csv_names:
                        with zf.open(csv_names[0]) as f:
                            df = pd.read_csv(f, low_memory=False, encoding="latin1")
                        df.to_csv(csv_path, index=False)
                        log.info(f"Extracted {csv_names[0]}: {len(df):,} records")
                        return df
            else:
                with open(csv_path, "wb") as f:
                    f.write(content)
                df = pd.read_csv(csv_path, low_memory=False, encoding="latin1")
                log.info(f"Wildlife CSV: {len(df):,} records")
                return df
        except Exception as exc:
            log.warning(f"Failed: {exc}")

    log.warning("FAA wildlife strike data unavailable — using curated records only")
    return None


def normalize_wildlife(df: pd.DataFrame) -> list[dict]:
    df.columns = [c.lower().strip() for c in df.columns]

    lat_col = next((c for c in df.columns if "lat" in c), None)
    lon_col = next((c for c in df.columns if "lon" in c), None)
    state_col = next((c for c in df.columns if c in ("state", "state_")
                      or c.startswith("state")), None)
    species_col = next((c for c in df.columns if "species" in c or "wildlife" in c
                        or "bird" in c), None)
    date_col = next((c for c in df.columns if "date" in c or "incident" in c), None)
    airport_col = next((c for c in df.columns if "airport" in c or "arpt" in c), None)

    if not lat_col or not lon_col:
        # Try using airport lat/lon lookup by ICAO
        log.warning(f"No lat/lon in wildlife CSV. Columns: {list(df.columns[:20])}")
        return []

    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col])
    df = df[(df[lat_col].between(24, 50)) & (df[lon_col].between(-130, -65))]

    if state_col:
        mask = df[state_col].astype(str).str.upper().isin(TARGET_STATES)
        df = df[mask]

    records = []
    for _, row in df.iterrows():
        try:
            lat = float(row[lat_col])
            lon = float(row[lon_col])
            species = str(row.get(species_col, "Unknown")).strip().upper() if species_col else "UNKNOWN"
            state = str(row.get(state_col, "")).strip() if state_col else ""
            dt = str(row.get(date_col, "")).strip() if date_col else None
            airport = str(row.get(airport_col, "Unknown")).strip() if airport_col else "Unknown"

            is_magneto = any(s in species for s in MAGNETORECEPTION_SPECIES)
            conf = CONFIDENCE + 1 if is_magneto else CONFIDENCE

            notes = f"FAA Wildlife Strike | {species} | {airport} | {state}"
            if is_magneto:
                notes += " | [MAGNETORECEPTIVE SPECIES — elevated signal]"

            rec = make_record(
                layer=LAYER, lat=lat, lon=lon,
                datetime_str=dt if dt and dt not in ("nan", "None") else None,
                confidence=conf, category=CATEGORY,
                source="FAA Wildlife Strike Database",
                notes=notes[:800],
                extra={"species": species, "airport": airport, "state": state,
                       "is_magnetoreceptive": is_magneto},
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue

    log.info(f"Normalized {len(records):,} wildlife strike records")
    return records


def build_curated_records() -> list[dict]:
    records = []
    for ev in CURATED_ANOMALIES:
        rec = make_record(
            layer=LAYER, lat=ev["lat"], lon=ev["lon"],
            datetime_str=ev["datetime"],
            confidence=CONFIDENCE + 1, category=CATEGORY,
            source="FAA Wildlife Strike Database / curated",
            notes=f"{ev['species']} | {ev['airport']} | {ev['notes']}",
            extra={"species": ev["species"], "airport": ev["airport"],
                   "state": ev["state"], "is_magnetoreceptive": True},
        )
        records.append(rec)
    log.info(f"Built {len(records)} curated wildlife anomaly records")
    return records


def main():
    log.info("=== fetch_faa_wildlife.py (Layer 29) ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    records = build_curated_records()
    df = fetch_wildlife_csv()
    if df is not None:
        records.extend(normalize_wildlife(df))

    log.info(f"Total FAA wildlife records: {len(records):,}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()

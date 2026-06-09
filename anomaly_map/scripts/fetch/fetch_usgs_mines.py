"""
Fetch USGS Mineral Resources Data System (MRDS) mine locations.

Source: USGS MRDS
Download: https://mrdata.usgs.gov/mrds/

Underground voids — mines, caverns, karst — create infrasound, gas channels,
and EM anomalies. Zone A (San Luis Valley, Uintah Basin) has extensive
uranium/coal extraction history. Karst terrain produces radon channels.

Last verified: 2026-06-09
"""

import sys
from io import StringIO
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, fetch_with_retry,
    get_logger, make_record, records_to_geojson, save_geojson, save_raw,
)

log = get_logger("fetch_usgs_mines")

LAYER = "usgs_mines"
CONFIDENCE = 4
CATEGORY = "subsurface"

RAW_DIR = RAW_DATA_DIR / "usgs_mines"
OUT_PATH = PROCESSED_DATA_DIR / "usgs_mines.geojson"

MRDS_CSV_URL = "https://mrdata.usgs.gov/mrds/mrds-csv.zip"
MRDS_CSV_ALT = "https://mrdata.usgs.gov/mrds/mrds.csv"

# States covering Zones A and B
TARGET_STATES = {"CO", "NM", "UT", "CA", "NV", "AZ", "WY", "MT", "ID"}

# High-interest commodity types
HIGH_INTEREST_COMMODITIES = {"U", "URAN", "URANIUM", "COAL", "TH", "THORIUM", "RN", "RADON"}
MEDIUM_INTEREST_COMMODITIES = {"AU", "GOLD", "AG", "SILVER", "CU", "COPPER", "Fe", "IRON"}

# Known high-interest mine clusters
CURATED_MINES = [
    {"name": "Uravan Uranium District", "lat": 38.3, "lon": -108.7, "state": "CO",
     "commodity": "Uranium", "status": "Abandoned",
     "notes": "Colorado Plateau uranium district. Extensive abandoned mines. High radon potential."},
    {"name": "San Juan Uranium Belt", "lat": 37.3, "lon": -107.8, "state": "CO",
     "commodity": "Uranium", "status": "Abandoned",
     "notes": "San Juan Mountains uranium. Zone A proximity. Carnotite ore deposits."},
    {"name": "Grants Uranium District NM", "lat": 35.1, "lon": -107.8, "state": "NM",
     "commodity": "Uranium", "status": "Partially active",
     "notes": "Largest uranium district in US. Ambrosia Lake mines. Rio Grande Rift proximity."},
    {"name": "Moab Uranium Tailings", "lat": 38.6, "lon": -109.5, "state": "UT",
     "commodity": "Uranium", "status": "Remediation",
     "notes": "Atlas Mill tailings site. Colorado River contamination. Uintah Basin proximity."},
    {"name": "San Luis Valley Coal (Raton Basin)", "lat": 37.0, "lon": -104.5, "state": "CO",
     "commodity": "Coal", "status": "Active/Abandoned",
     "notes": "Raton Basin coalfields adjacent to San Luis Valley UAP zone."},
    {"name": "Book Cliffs Coal (Utah)", "lat": 39.5, "lon": -109.5, "state": "UT",
     "commodity": "Coal", "status": "Active",
     "notes": "Uintah Basin coal mines. Methane outgassing documented. Skinwalker Ranch proximity."},
    {"name": "Creede Mining District", "lat": 37.8, "lon": -106.9, "state": "CO",
     "commodity": "Silver/Gold", "status": "Abandoned",
     "notes": "San Luis Valley adjacent. Extensive underground workings. Rio Grande Rift geology."},
    {"name": "Eureka/Tintic District", "lat": 40.0, "lon": -112.1, "state": "UT",
     "commodity": "Lead/Silver", "status": "Abandoned",
     "notes": "Extensive Utah mine workings. Dugway proximity."},
]


def fetch_mrds_csv() -> pd.DataFrame | None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = RAW_DIR / "mrds.csv"
    if csv_path.exists():
        log.info(f"Using cached MRDS CSV: {csv_path}")
        return pd.read_csv(csv_path, low_memory=False, encoding="latin1")

    for url in [MRDS_CSV_URL, MRDS_CSV_ALT]:
        log.info(f"Fetching MRDS from {url}…")
        try:
            resp = fetch_with_retry(url, stream=True, logger=log)
            content = resp.content

            if url.endswith(".zip"):
                import zipfile, io
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
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
                log.info(f"MRDS CSV: {len(df):,} records")
                return df
        except Exception as exc:
            log.warning(f"Failed: {exc}")

    log.warning("MRDS CSV unavailable — using curated mines only")
    return None


def normalize_mrds(df: pd.DataFrame) -> list[dict]:
    df.columns = [c.lower().strip() for c in df.columns]
    lat_col = next((c for c in df.columns if "lat" in c), None)
    lon_col = next((c for c in df.columns if "lon" in c or "lng" in c), None)
    name_col = next((c for c in df.columns if "name" in c or "dep_name" in c), None)
    state_col = next((c for c in df.columns if "state" in c), None)
    commodity_col = next((c for c in df.columns if "commod" in c or "primary" in c), None)
    status_col = next((c for c in df.columns if "oper_type" in c or "status" in c or "dev_stat" in c), None)

    if not lat_col or not lon_col:
        log.warning(f"No lat/lon found. Columns: {list(df.columns[:20])}")
        return []

    # Filter to target states
    if state_col:
        df = df[df[state_col].str.upper().isin(TARGET_STATES)]

    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col])
    df = df[(df[lat_col].between(24, 50)) & (df[lon_col].between(-130, -65))]

    records = []
    for _, row in df.iterrows():
        try:
            commodity = str(row.get(commodity_col, "Unknown")).upper().strip() if commodity_col else "Unknown"
            status = str(row.get(status_col, "Unknown")).strip() if status_col else "Unknown"
            name = str(row.get(name_col, "Unknown mine")).strip() if name_col else "MRDS site"
            state = str(row.get(state_col, "")).strip() if state_col else ""

            is_uranium = any(u in commodity for u in HIGH_INTEREST_COMMODITIES)
            conf = 5 if is_uranium else CONFIDENCE

            notes = f"{name} | {commodity} | {status} | {state}"
            if is_uranium:
                notes += " | [URANIUM — HIGH INTEREST: radon/radiation connection]"

            rec = make_record(
                layer=LAYER, lat=float(row[lat_col]), lon=float(row[lon_col]),
                confidence=conf, category=CATEGORY,
                source="USGS MRDS",
                notes=notes,
                extra={"mine_name": name, "commodity": commodity,
                       "status": status, "state": state, "is_uranium": is_uranium},
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue

    log.info(f"Normalized {len(records):,} MRDS records")
    return records


def build_curated_records() -> list[dict]:
    records = []
    for mine in CURATED_MINES:
        try:
            is_uranium = "uranium" in mine["commodity"].lower()
            rec = make_record(
                layer=LAYER, lat=mine["lat"], lon=mine["lon"],
                confidence=5 if is_uranium else CONFIDENCE,
                category=CATEGORY,
                source="USGS MRDS / curated",
                notes=f"{mine['name']} | {mine['commodity']} | {mine['status']} | {mine['notes']}",
                extra={"mine_name": mine["name"], "commodity": mine["commodity"],
                       "status": mine["status"], "state": mine["state"],
                       "is_uranium": is_uranium},
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue
    log.info(f"Built {len(records)} curated mine records")
    return records


def main():
    log.info("=== fetch_usgs_mines.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    records = build_curated_records()
    df = fetch_mrds_csv()
    if df is not None:
        records.extend(normalize_mrds(df))
    log.info(f"Total mine records: {len(records):,}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()

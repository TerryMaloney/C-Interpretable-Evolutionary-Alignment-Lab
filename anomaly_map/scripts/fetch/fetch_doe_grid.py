"""
Fetch DOE Power Grid Disturbance Reports (OE-417 Electric Emergency Incident Reports).

Source: US Department of Energy, Office of Electricity
Download: https://www.oe.netl.doe.gov/OE417.aspx
Annual Excel files available for each year.

Note: OE-417 data includes NERC region, not precise facility coordinates.
This script maps NERC region centroids to approximate lat/lon.
"Unknown cause" events are flagged as highest interest for this analysis.

Last verified: 2026-06-09

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  nerc_region, event_type, cause, customers_affected, area_affected
"""

import sys
from io import BytesIO
from pathlib import Path

import pandas as pd

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

log = get_logger("fetch_doe_grid")

LAYER = "doe_grid"
CONFIDENCE = 4
CATEGORY = "em_disturbance"

RAW_DIR = RAW_DATA_DIR / "doe_grid"
OUT_PATH = PROCESSED_DATA_DIR / "doe_grid.geojson"

# OE-417 annual summary Excel files (update URLs as DOE publishes new years)
OE417_URLS = {
    2021: "https://www.oe.netl.doe.gov/OE417_Annual_Summary.aspx",
    2022: "https://www.oe.netl.doe.gov/OE417_Annual_Summary.aspx",
    2023: "https://www.oe.netl.doe.gov/OE417_Annual_Summary.aspx",
}

# Direct Excel download URL pattern (verify on OE417 page)
OE417_EXCEL_BASE = "https://www.oe.netl.doe.gov/OE417_event_summary_{year}.xlsx"

# NERC region approximate centroids (WGS84)
NERC_CENTROIDS = {
    "WECC":   (39.5, -111.5),   # Western Electricity Coordinating Council
    "MRO":    (46.0, -96.0),    # Midwest Reliability Organization
    "NPCC":   (43.5, -74.0),    # Northeast Power Coordinating Council
    "RFC":    (40.5, -80.0),    # ReliabilityFirst Corporation
    "SERC":   (34.0, -85.0),    # SERC Reliability Corporation
    "SPP":    (37.0, -97.0),    # Southwest Power Pool
    "TRE":    (31.5, -99.0),    # Texas RE (ERCOT)
    "FRCC":   (28.0, -81.5),    # Florida Reliability Coordinating Council
    "HI":     (20.5, -157.0),   # Hawaii
    "AK":     (64.0, -153.0),   # Alaska
}

UNKNOWN_CAUSE_KEYWORDS = [
    "unknown", "undetermined", "under investigation", "unexplained",
    "suspicious", "vandalism", "physical attack", "cyber",
]


def fetch_excel(year: int) -> pd.DataFrame | None:
    url = OE417_EXCEL_BASE.format(year=year)
    log.info(f"Fetching OE-417 Excel for {year}: {url}")
    try:
        resp = fetch_with_retry(url, logger=log)
        raw_path = RAW_DIR / f"oe417_{year}.xlsx"
        save_raw(resp.content, raw_path)
        df = pd.read_excel(BytesIO(resp.content), engine="openpyxl", header=0)
        log.info(f"  {year}: {len(df)} rows")
        return df
    except Exception as exc:
        log.warning(f"  Could not fetch {year}: {exc}")
        return None


def normalize(df: pd.DataFrame, year: int) -> list[dict]:
    df.columns = [str(c).lower().strip().replace(" ", "_").replace("/", "_") for c in df.columns]

    date_col = next((c for c in df.columns if "date" in c and "event" in c), None) or \
               next((c for c in df.columns if "date" in c), None)
    nerc_col = next((c for c in df.columns if "nerc" in c), None)
    cause_col = next((c for c in df.columns if "cause" in c), None)
    type_col = next((c for c in df.columns if "type" in c or "event_type" in c), None)
    area_col = next((c for c in df.columns if "area" in c), None)
    customers_col = next((c for c in df.columns if "customer" in c), None)

    records = []
    for _, row in df.iterrows():
        try:
            nerc = str(row[nerc_col]).strip().upper() if nerc_col else "UNKNOWN"
            nerc_key = next((k for k in NERC_CENTROIDS if k in nerc), None)
            if not nerc_key:
                # Try partial match
                nerc_key = next((k for k in NERC_CENTROIDS if nerc.startswith(k)), "WECC")

            lat, lon = NERC_CENTROIDS.get(nerc_key, (38.0, -97.0))

            cause = str(row[cause_col]).strip() if cause_col and pd.notna(row.get(cause_col)) else "Unknown"
            event_type = str(row[type_col]).strip() if type_col and pd.notna(row.get(type_col)) else ""
            area = str(row[area_col]).strip() if area_col and pd.notna(row.get(area_col)) else ""
            customers = row[customers_col] if customers_col and pd.notna(row.get(customers_col)) else None

            dt_str = None
            if date_col and pd.notna(row.get(date_col)):
                try:
                    dt_str = pd.to_datetime(row[date_col]).isoformat()
                except Exception:
                    dt_str = str(row[date_col])

            # Flag analytically interesting events
            cause_lower = cause.lower()
            is_unknown = any(kw in cause_lower for kw in UNKNOWN_CAUSE_KEYWORDS)

            notes = f"NERC:{nerc_key} | {event_type} | Cause: {cause}"
            if area:
                notes += f" | {area}"
            if is_unknown:
                notes += " | [UNKNOWN CAUSE — HIGH INTEREST]"

            rec = make_record(
                layer=LAYER,
                lat=lat,
                lon=lon,
                datetime_str=dt_str,
                confidence=CONFIDENCE,
                category=CATEGORY,
                source=f"DOE OE-417 ({year})",
                notes=notes,
                extra={
                    "nerc_region": nerc_key,
                    "event_type": event_type,
                    "cause": cause,
                    "customers_affected": customers,
                    "area_affected": area,
                    "unknown_cause": is_unknown,
                },
            )
            records.append(rec)
        except Exception:
            continue
    return records


def main():
    log.info("=== fetch_doe_grid.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_records = []
    current_year = 2026
    for year in range(2012, current_year + 1):
        df = fetch_excel(year)
        if df is not None and len(df) > 0:
            records = normalize(df, year)
            all_records.extend(records)
            log.info(f"  Year {year}: {len(records)} normalized records")

    if not all_records:
        log.error(
            "No OE-417 data fetched. Manual download option:\n"
            "  Visit https://www.oe.netl.doe.gov/OE417.aspx\n"
            "  Download annual Excel summaries to data/raw/doe_grid/\n"
            "  Re-run this script — it will find local files automatically"
        )
        # Try local files
        for xlsx_file in sorted(RAW_DIR.glob("oe417_*.xlsx")):
            year = int(xlsx_file.stem.split("_")[-1])
            try:
                df = pd.read_excel(xlsx_file, engine="openpyxl")
                records = normalize(df, year)
                all_records.extend(records)
                log.info(f"Loaded local {xlsx_file.name}: {len(records)} records")
            except Exception as exc:
                log.warning(f"Failed to read {xlsx_file}: {exc}")

    log.info(f"Total grid disturbance records: {len(all_records):,}")
    gj = records_to_geojson(all_records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()

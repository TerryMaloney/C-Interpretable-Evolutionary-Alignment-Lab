"""
Process manual CSV datasets from data/manual/ into standard GeoJSON.

EXTENSIBILITY ENTRY POINT — how to add a new dataset:
  1. Create a CSV in data/manual/ with these columns (at minimum):
       lat, lon, datetime (optional), source, notes
  2. Optionally add an entry to data/layer_registry.json
  3. Run: python scripts/process/geocode_manual.py
  4. Done — output appears in data/processed/<filename>.geojson

The script auto-detects all CSV files in data/manual/ and processes them.
Layer name is taken from the filename (without extension).
If the layer is in layer_registry.json, its confidence and category are used;
otherwise defaults apply.

Addresses/place names in 'address' column are geocoded via Nominatim if
lat/lon are missing. Direct lat/lon columns are used without geocoding.
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    MANUAL_DATA_DIR,
    PROCESSED_DATA_DIR,
    get_logger,
    load_registry,
    make_record,
    records_to_geojson,
    save_geojson,
)

log = get_logger("geocode_manual")

DEFAULT_CONFIDENCE = 2
DEFAULT_CATEGORY = "manual"


def geocode_address(address: str) -> tuple[float, float] | None:
    """Geocode an address string using Nominatim. Returns (lat, lon) or None."""
    try:
        import time
        from geopy.geocoders import Nominatim
        geocoder = Nominatim(user_agent="anomaly_map_geocoder/1.0")
        location = geocoder.geocode(address, timeout=10)
        time.sleep(1.1)  # Nominatim rate limit
        if location:
            return location.latitude, location.longitude
    except Exception as exc:
        log.warning(f"Geocoding failed for '{address}': {exc}")
    return None


def process_csv(csv_path: Path, registry: dict) -> list[dict]:
    layer_name = csv_path.stem
    layer_meta = registry.get("layers", {}).get(layer_name, {})

    confidence = layer_meta.get("confidence", DEFAULT_CONFIDENCE)
    category = layer_meta.get("category", DEFAULT_CATEGORY)
    layer_display = layer_meta.get("name", layer_name)

    log.info(f"Processing {csv_path.name} → layer '{layer_name}' (confidence={confidence})")

    records = []
    skipped = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        fieldnames_lower = [fn.lower().strip() for fn in fieldnames]

        # Map column names (case-insensitive)
        col_map = {fn.lower().strip(): fn for fn in fieldnames}

        for row_num, row in enumerate(reader, 2):
            row_lower = {k.lower().strip(): v for k, v in row.items()}

            # Resolve lat/lon
            lat = None
            lon = None
            for lat_key in ("lat", "latitude", "y"):
                if lat_key in row_lower and row_lower[lat_key].strip():
                    try:
                        lat = float(row_lower[lat_key])
                    except ValueError:
                        pass
                    break

            for lon_key in ("lon", "lng", "longitude", "x"):
                if lon_key in row_lower and row_lower[lon_key].strip():
                    try:
                        lon = float(row_lower[lon_key])
                    except ValueError:
                        pass
                    break

            # Try geocoding if lat/lon missing but address present
            if (lat is None or lon is None) and "address" in row_lower:
                address = row_lower["address"].strip()
                if address:
                    result = geocode_address(address)
                    if result:
                        lat, lon = result
                    else:
                        log.warning(f"Row {row_num}: could not geocode '{address}'")
                        skipped += 1
                        continue

            if lat is None or lon is None:
                skipped += 1
                continue

            # Resolve optional fields — allow CSV to override registry defaults
            dt = row_lower.get("datetime", "").strip() or row_lower.get("date", "").strip() or None
            if dt == "":
                dt = None

            row_conf = row_lower.get("confidence", "").strip()
            if row_conf:
                try:
                    confidence_final = int(float(row_conf))
                except ValueError:
                    confidence_final = confidence
            else:
                confidence_final = confidence

            row_cat = row_lower.get("category", "").strip() or category
            source = row_lower.get("source", "").strip() or f"Manual dataset: {csv_path.name}"
            notes = row_lower.get("notes", "").strip() or ""

            # Collect any extra fields not in standard set
            standard_keys = {"lat", "lon", "latitude", "longitude", "x", "y",
                             "datetime", "date", "confidence", "category", "source", "notes", "address"}
            extra_fields = {
                k: v for k, v in row_lower.items()
                if k not in standard_keys and v and v.strip()
            }

            try:
                rec = make_record(
                    layer=layer_name,
                    lat=lat,
                    lon=lon,
                    datetime_str=dt,
                    confidence=confidence_final,
                    category=row_cat,
                    source=source,
                    notes=notes[:1000] if notes else None,
                    extra=extra_fields if extra_fields else None,
                )
                records.append(rec)
            except ValueError as exc:
                log.warning(f"Row {row_num}: {exc}")
                skipped += 1

    log.info(f"  Processed: {len(records)} records, skipped: {skipped}")
    return records


def main(target: str | None = None):
    """
    Process manual CSVs.
    target: specific filename stem to process (None = process all)
    """
    log.info("=== geocode_manual.py ===")
    registry = load_registry()

    csv_files = sorted(MANUAL_DATA_DIR.glob("*.csv"))
    if not csv_files:
        log.warning(f"No CSV files found in {MANUAL_DATA_DIR}")
        return

    if target:
        csv_files = [f for f in csv_files if f.stem == target]
        if not csv_files:
            log.error(f"No CSV found with stem '{target}'")
            return

    total_records = 0
    for csv_path in csv_files:
        records = process_csv(csv_path, registry)
        if records:
            gj = records_to_geojson(records)
            out_path = PROCESSED_DATA_DIR / f"{csv_path.stem}.geojson"
            save_geojson(gj, out_path)
            log.info(f"  Saved {len(records)} records → {out_path}")
            total_records += len(records)

    log.info(f"Total records written: {total_records}")


if __name__ == "__main__":
    import sys
    target_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(target_arg)

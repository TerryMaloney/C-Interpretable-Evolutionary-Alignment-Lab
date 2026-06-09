"""
Normalize all processed GeoJSON files to strict standard schema.

Reads every .geojson file from data/processed/, validates each record
against the required schema, rejects invalid records, and writes
validated output to output/layers/<layer>.geojson.

Required fields per record: id, layer, lat, lon
Optional: datetime, confidence, category, source, notes

Run after all fetch scripts and geocode_manual.py have completed.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    OUTPUT_DIR,
    PROCESSED_DATA_DIR,
    get_logger,
    load_registry,
    records_to_geojson,
    save_geojson,
)

log = get_logger("normalize_all")

REQUIRED_FIELDS = {"id", "layer", "lat", "lon"}
OPTIONAL_FIELDS = {"datetime", "confidence", "category", "source", "notes"}
LAYERS_OUTPUT_DIR = OUTPUT_DIR / "layers"


def validate_record(record: dict, layer_meta: dict) -> dict | None:
    """
    Validate and fill defaults for a record.
    Returns cleaned record or None if invalid.
    """
    props = record.get("properties", record)

    # For GeoJSON features, merge geometry coordinates into record
    if "geometry" in record:
        geom = record.get("geometry", {})
        coords = geom.get("coordinates", [])
        if len(coords) >= 2:
            props = dict(props)
            props["lon"] = coords[0]
            props["lat"] = coords[1]

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in props or props[field] is None:
            return None

    try:
        lat = float(props["lat"])
        lon = float(props["lon"])
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None
    except (ValueError, TypeError):
        return None

    # Apply registry defaults if missing
    if "confidence" not in props or props["confidence"] is None:
        props["confidence"] = layer_meta.get("confidence", 2)
    if "category" not in props or props["category"] is None:
        props["category"] = layer_meta.get("category", "unknown")
    if "datetime" not in props:
        props["datetime"] = None

    return {
        "id": props.get("id", ""),
        "layer": props.get("layer", ""),
        "lat": lat,
        "lon": lon,
        "datetime": props.get("datetime"),
        "confidence": props.get("confidence"),
        "category": props.get("category"),
        "source": props.get("source"),
        "notes": props.get("notes"),
        **{k: v for k, v in props.items()
           if k not in REQUIRED_FIELDS | OPTIONAL_FIELDS | {"lat", "lon"}},
    }


def normalize_file(geojson_path: Path, registry: dict) -> tuple[list[dict], int]:
    layer_name = geojson_path.stem
    layer_meta = registry.get("layers", {}).get(layer_name, {})

    with open(geojson_path) as f:
        data = json.load(f)

    features = data.get("features", [])
    valid_records = []
    rejected = 0

    for feat in features:
        cleaned = validate_record(feat, layer_meta)
        if cleaned:
            valid_records.append(cleaned)
        else:
            rejected += 1

    return valid_records, rejected


def main():
    log.info("=== normalize_all.py ===")
    registry = load_registry()
    LAYERS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    geojson_files = sorted(PROCESSED_DATA_DIR.glob("*.geojson"))
    if not geojson_files:
        log.warning(f"No .geojson files in {PROCESSED_DATA_DIR}")
        return

    summary = {}
    total_valid = 0
    total_rejected = 0

    for path in geojson_files:
        log.info(f"Normalizing {path.name}…")
        try:
            records, rejected = normalize_file(path, registry)
            layer_name = path.stem

            gj = records_to_geojson(records)
            out_path = LAYERS_OUTPUT_DIR / path.name
            save_geojson(gj, out_path)

            summary[layer_name] = {"valid": len(records), "rejected": rejected}
            total_valid += len(records)
            total_rejected += rejected
            log.info(f"  {layer_name}: {len(records)} valid, {rejected} rejected → {out_path}")
        except Exception as exc:
            log.error(f"  Failed to normalize {path.name}: {exc}")

    log.info(f"\nNormalization complete:")
    log.info(f"  Total valid records: {total_valid:,}")
    log.info(f"  Total rejected: {total_rejected:,}")
    log.info(f"  Output: {LAYERS_OUTPUT_DIR}")

    # Write summary
    summary_path = OUTPUT_DIR / "analysis" / "normalization_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump({"summary": summary, "total_valid": total_valid, "total_rejected": total_rejected}, f, indent=2)
    log.info(f"  Summary → {summary_path}")


if __name__ == "__main__":
    main()

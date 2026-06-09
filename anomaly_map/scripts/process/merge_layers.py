"""
Merge all normalized layer GeoJSON files into a single combined GeoJSON.

Reads from output/layers/*.geojson
Writes to output/combined.geojson

Also writes a layer manifest listing what's in the combined file.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import OUTPUT_DIR, get_logger, load_registry, save_geojson

log = get_logger("merge_layers")

LAYERS_DIR = OUTPUT_DIR / "layers"
COMBINED_PATH = OUTPUT_DIR / "combined.geojson"


def main():
    log.info("=== merge_layers.py ===")
    registry = load_registry()

    layer_files = sorted(LAYERS_DIR.glob("*.geojson"))
    if not layer_files:
        log.warning(f"No layer files in {LAYERS_DIR}. Run normalize_all.py first.")
        return

    all_features = []
    manifest = []

    for path in layer_files:
        layer_name = path.stem
        layer_meta = registry.get("layers", {}).get(layer_name, {})
        tier = layer_meta.get("tier", "?")

        try:
            with open(path) as f:
                data = json.load(f)
            features = data.get("features", [])
            all_features.extend(features)
            manifest.append({
                "layer": layer_name,
                "display_name": layer_meta.get("name", layer_name),
                "tier": tier,
                "confidence": layer_meta.get("confidence"),
                "category": layer_meta.get("category"),
                "record_count": len(features),
                "file": str(path.relative_to(OUTPUT_DIR)),
            })
            log.info(f"  {layer_name}: {len(features):,} features (Tier {tier})")
        except Exception as exc:
            log.error(f"  Failed to load {path.name}: {exc}")

    combined = {
        "type": "FeatureCollection",
        "features": all_features,
        "metadata": {
            "total_records": len(all_features),
            "layers": len(manifest),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    save_geojson(combined, COMBINED_PATH)
    log.info(f"\nMerged {len(all_features):,} total records from {len(manifest)} layers → {COMBINED_PATH}")

    manifest_path = OUTPUT_DIR / "layer_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump({"layers": manifest, "total_records": len(all_features)}, f, indent=2)
    log.info(f"Manifest → {manifest_path}")


if __name__ == "__main__":
    main()

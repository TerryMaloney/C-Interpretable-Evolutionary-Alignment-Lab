"""
PMTiles Build Script
Converts processed GeoJSON layers to PMTiles format for efficient static serving.

PMTiles is a single-file archive of pyramidal map tiles.
- No tile server required — serve from S3, Cloudflare R2, Vercel, or any CDN
- Progressive loading: only tiles for current viewport are fetched
- Prevents browser crash from loading 50M+ raw records into DeckGL

Architecture:
  Python fetch scripts → GeoJSON → Tippecanoe → PMTiles → static CDN
  DeckGL app → MVTLayer (PMTiles) → loads tiles on demand

Requirements:
  pip install pmtiles tippecanoe (or install tippecanoe binary)
  tippecanoe must be on PATH (brew install tippecanoe or apt-get install tippecanoe)
"""
import os, sys, json, subprocess, argparse, shutil, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("build_pmtiles")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = REPO_ROOT / "anomaly_map/data/processed"
OUTPUT_DIR = REPO_ROOT / "anomaly_map/output/pmtiles"
MERGED_GEOJSON = REPO_ROOT / "anomaly_map/output/layers/merged_all_layers.geojson"

# Layers that benefit most from PMTiles (large datasets)
LARGE_LAYERS = [
    "nuforc",           # ~150,000 records
    "usgs_seismic",     # ~50,000/yr
    "firms_thermal",    # ~1M events
    "faa_wildlife_strikes",  # ~200k
    "usgs_mines",       # ~100k mines
    "water_wells",      # ~50k wells
    "bluebook_unknowns",    # ~700 cases (small but good PMTiles demo)
    "geipan_cat_d",         # ~700 cases
]

# Tippecanoe zoom range config per layer type
ZOOM_CONFIGS = {
    "default": {"min_zoom": 2, "max_zoom": 14},
    "nuforc":  {"min_zoom": 3, "max_zoom": 16},  # Dense point layer
    "usgs_seismic": {"min_zoom": 2, "max_zoom": 14},
    "firms_thermal": {"min_zoom": 3, "max_zoom": 14},
}


def check_tippecanoe():
    if shutil.which("tippecanoe") is None:
        logger.error("tippecanoe not found on PATH.")
        logger.error("Install: brew install tippecanoe  OR  apt-get install tippecanoe")
        logger.error("Or build from source: https://github.com/felt/tippecanoe")
        return False
    version = subprocess.run(["tippecanoe", "--version"], capture_output=True, text=True)
    logger.info(f"tippecanoe: {version.stdout.strip() or version.stderr.strip()}")
    return True


def check_pmtiles_tool():
    """Check if pmtiles CLI is available for conversion."""
    if shutil.which("pmtiles") is not None:
        return True
    logger.warning("pmtiles CLI not found — will use .mbtiles output only")
    logger.warning("Install: go install github.com/protomaps/go-pmtiles/cmd/pmtiles@latest")
    return False


def build_layer_pmtiles(layer_name: str, geojson_path: Path, output_dir: Path) -> bool:
    """Convert a single GeoJSON layer to PMTiles via Tippecanoe."""
    mbtiles_path = output_dir / f"{layer_name}.mbtiles"
    pmtiles_path = output_dir / f"{layer_name}.pmtiles"

    zoom = ZOOM_CONFIGS.get(layer_name, ZOOM_CONFIGS["default"])
    min_z = zoom["min_zoom"]
    max_z = zoom["max_zoom"]

    # Tippecanoe options:
    # -z max zoom, -Z min zoom
    # --drop-densest-as-needed: thin points at low zoom (prevents memory crash)
    # --force: overwrite existing output
    # --generate-ids: add feature IDs for PMTiles spec
    # --read-parallel: speed up large files
    cmd = [
        "tippecanoe",
        "-o", str(mbtiles_path),
        "-Z", str(min_z),
        "-z", str(max_z),
        "-l", layer_name,
        "--drop-densest-as-needed",
        "--force",
        "--generate-ids",
        "--quiet",
        str(geojson_path),
    ]

    logger.info(f"Building {layer_name} → {mbtiles_path.name} (zoom {min_z}–{max_z})...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"Tippecanoe failed for {layer_name}: {result.stderr[:500]}")
            return False
        logger.info(f"  ✓ {mbtiles_path.stat().st_size // 1024}KB")
    except subprocess.TimeoutExpired:
        logger.error(f"Tippecanoe timed out for {layer_name}")
        return False
    except FileNotFoundError:
        logger.error("tippecanoe not found")
        return False

    # Convert mbtiles → pmtiles if pmtiles CLI available
    if shutil.which("pmtiles"):
        try:
            conv = subprocess.run(
                ["pmtiles", "convert", str(mbtiles_path), str(pmtiles_path)],
                capture_output=True, text=True, timeout=120
            )
            if conv.returncode == 0:
                logger.info(f"  ✓ {pmtiles_path.name} ({pmtiles_path.stat().st_size // 1024}KB)")
                mbtiles_path.unlink()  # Remove intermediate
                return True
            else:
                logger.warning(f"pmtiles convert failed: {conv.stderr[:300]}")
        except Exception as e:
            logger.warning(f"pmtiles convert error: {e}")

    # Fall back to keeping .mbtiles (compatible with MapLibre via mbtiles-source or tile server)
    logger.info(f"  → Kept as {mbtiles_path.name} (no pmtiles CLI)")
    return True


def build_convergence_pmtiles(convergence_geojson: Path, output_dir: Path) -> bool:
    """Build PMTiles for the pre-computed C-Score heatmap (default boot layer)."""
    mbtiles_path = output_dir / "convergence_scores.mbtiles"
    pmtiles_path = output_dir / "convergence_scores.pmtiles"

    if not convergence_geojson.exists():
        logger.warning(f"Convergence GeoJSON not found: {convergence_geojson}")
        logger.warning("Run: python scripts/analyze/convergence_score.py --mode grid first")
        return False

    cmd = [
        "tippecanoe",
        "-o", str(mbtiles_path),
        "-Z", "2", "-z", "12",
        "-l", "convergence_scores",
        "--drop-densest-as-needed",
        "--force",
        "--generate-ids",
        "--quiet",
        str(convergence_geojson),
    ]

    logger.info("Building convergence scores PMTiles (default boot layer)...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error(f"Tippecanoe failed for convergence: {result.stderr[:500]}")
            return False
        logger.info(f"  ✓ convergence_scores: {mbtiles_path.stat().st_size // 1024}KB")

        if shutil.which("pmtiles"):
            subprocess.run(
                ["pmtiles", "convert", str(mbtiles_path), str(pmtiles_path)],
                capture_output=True, timeout=180
            )
            if pmtiles_path.exists():
                mbtiles_path.unlink()
                logger.info(f"  ✓ {pmtiles_path.name}")
        return True
    except Exception as e:
        logger.error(f"Convergence PMTiles build failed: {e}")
        return False


def write_pmtiles_manifest(output_dir: Path, built_layers: list):
    """Write a manifest JSON for the app to know which PMTiles are available."""
    manifest = {
        "pmtiles_available": built_layers,
        "base_path": "/pmtiles",
        "format": "pmtiles",
        "note": "If pmtiles not available, fall back to /data/processed/{layer}.geojson",
        "serve_instructions": {
            "vercel": "Copy pmtiles/ to public/pmtiles/",
            "cloudflare_r2": "Upload to R2 bucket with public access",
            "s3": "Upload to S3 with CloudFront, set CORS for Range requests",
            "local": "python -m http.server 8080 from output/pmtiles/ parent",
        }
    }
    manifest_path = output_dir / "pmtiles_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Manifest → {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="Build PMTiles for Anomaly Map layers")
    parser.add_argument("--layers", nargs="+", default=None,
                        help="Specific layers to build (default: all large layers)")
    parser.add_argument("--all", action="store_true",
                        help="Build all processed GeoJSON layers")
    parser.add_argument("--convergence-only", action="store_true",
                        help="Build only the convergence scores PMTiles")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help=f"Output directory (default: {OUTPUT_DIR})")
    args = parser.parse_args()

    if not check_tippecanoe():
        sys.exit(1)

    has_pmtiles = check_pmtiles_tool()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output → {output_dir}")

    built = []

    # Build convergence scores first (default boot layer)
    convergence_geojson = REPO_ROOT / "anomaly_map/output/analysis/convergence_scores.geojson"
    if not args.convergence_only or True:
        if build_convergence_pmtiles(convergence_geojson, output_dir):
            built.append("convergence_scores")

    if args.convergence_only:
        write_pmtiles_manifest(output_dir, built)
        logger.info(f"Done. Built: {built}")
        return

    # Determine which layers to build
    if args.all:
        layer_files = sorted(PROCESSED_DIR.glob("*.geojson"))
        target_layers = [f.stem for f in layer_files]
    elif args.layers:
        target_layers = args.layers
    else:
        target_layers = LARGE_LAYERS

    for layer_name in target_layers:
        geojson_path = PROCESSED_DIR / f"{layer_name}.geojson"
        if not geojson_path.exists():
            logger.warning(f"Skipping {layer_name} — GeoJSON not found at {geojson_path}")
            continue
        if build_layer_pmtiles(layer_name, geojson_path, output_dir):
            built.append(layer_name)

    write_pmtiles_manifest(output_dir, built)
    logger.info(f"\nBuild complete. {len(built)} layers built: {built}")

    if not has_pmtiles:
        logger.info("\nTo serve PMTiles from .mbtiles, options:")
        logger.info("  1. Install pmtiles CLI and re-run for true PMTiles format")
        logger.info("  2. Use Martin tile server: https://github.com/maplibre/martin")
        logger.info("  3. Use MapLibre GL JS mbtiles source plugin for local dev")


if __name__ == "__main__":
    main()

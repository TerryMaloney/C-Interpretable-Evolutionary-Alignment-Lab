"""
Fetch ESA Sentinel-5P TROPOMI atmospheric chemistry data.

Source: ESA Copernicus Programme — Sentinel-5 Precursor
Portal: https://scihub.copernicus.eu (registration required)
Alternative: Google Earth Engine (no download, cloud processing)

Physics basis: Chemistry. Propulsion systems and underground/underwater
processes produce combustion products and outgassing signatures.

Products of interest:
  CH4 (methane):    Underground geological/industrial sources
  SO2 (sulfur):     Combustion, volcanic/hydrothermal
  NO2 (nitrogen):   Combustion in unpopulated areas
  Aerosol index:    Particulate emissions

Coverage: Global daily, 3.5x5.5km resolution, 2017–present

Analysis target:
  - Persistent SO2/NO2 plumes over non-volcanic, non-industrial zones
  - CH4 hotspots outside known oil/gas infrastructure
  - Anomalies correlating with Zone A (Rio Grande Rift) and Zone B (Catalina offshore)

Last verified: 2026-06-09

Output schema:
  id, layer, lat, lon, datetime, confidence, category, source, notes,
  product, column_density, qa_value
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, get_logger,
    make_record, records_to_geojson, save_geojson,
)

log = get_logger("fetch_sentinel5p")

LAYER = "sentinel5p_atmos"
CONFIDENCE = 4
CATEGORY = "atmospheric"

RAW_DIR = RAW_DATA_DIR / "sentinel5p"
OUT_PATH = PROCESSED_DATA_DIR / "sentinel5p_atmos.geojson"

COPERNICUS_USER = os.getenv("COPERNICUS_USER", "")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASS", "")

# Zones of interest bounding boxes
ZONES = {
    "A": "POLYGON((-112 30,-104 30,-104 45,-112 45,-112 30))",
    "B": "POLYGON((-121 29,-116 29,-116 35,-121 35,-121 29))",
    "E": "POLYGON((130 30,150 30,150 45,130 45,130 30))",
}

# Products to fetch
PRODUCTS = {
    "L2__SO2___": {"name": "SO2", "interest": "Combustion/volcanic — unpopulated zones"},
    "L2__NO2___": {"name": "NO2", "interest": "Combustion in unpopulated areas"},
    "L2__CH4___": {"name": "CH4 (methane)", "interest": "Geological/underground sources"},
}

# Anomaly thresholds (mol/m² for trace gases, unitless for aerosol)
THRESHOLDS = {
    "SO2": 0.001,    # mol/m²
    "NO2": 0.0001,   # mol/m²
    "CH4": 1900,     # ppb
}

GEE_SCRIPT_TEMPLATE = """
// Google Earth Engine script for Sentinel-5P {product_name} analysis
// Run this at: https://code.earthengine.google.com/

var zone = ee.Geometry.Polygon({geojson_bbox});
var startDate = '{start}';
var endDate = '{end}';

var s5p = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_{product_id}')
  .filterDate(startDate, endDate)
  .filterBounds(zone)
  .select('{band}');

// Monthly median composite (cloud-masked)
var monthly = s5p.mean().clip(zone);

// Compute anomaly (deviation from global mean)
var globalMean = s5p.mean().reduceRegion({{
  reducer: ee.Reducer.mean(),
  geometry: zone,
  scale: 7000,
  maxPixels: 1e9
}});

// Export to Drive
Export.image.toDrive({{
  image: monthly,
  description: 'S5P_{product_name}_Zone_{zone}_monthly',
  scale: 7000,
  region: zone,
  fileFormat: 'GeoTIFF'
}});

print('Zone stats:', globalMean);
"""


def try_sentinelsat_api(product_type: str, product_info: dict, zone_name: str, zone_wkt: str) -> list[dict]:
    """Try to download via sentinelsat API (requires Copernicus account)."""
    try:
        from sentinelsat import SentinelAPI, geojson_to_wkt
    except ImportError:
        return []

    if not COPERNICUS_USER or not COPERNICUS_PASS:
        return []

    try:
        api = SentinelAPI(COPERNICUS_USER, COPERNICUS_PASS, "https://scihub.copernicus.eu/dhus")

        products = api.query(
            area=zone_wkt,
            date=("20230601", "20231201"),
            platformname="Sentinel-5 Precursor",
            producttype=product_type,
        )

        log.info(f"  sentinelsat found {len(products)} {product_info['name']} products for Zone {zone_name}")
        return list(products.values())
    except Exception as exc:
        log.warning(f"  sentinelsat query failed: {exc}")
        return []


def generate_gee_scripts():
    """Write Google Earth Engine scripts for manual cloud-based processing."""
    gee_dir = RAW_DIR / "gee_scripts"
    gee_dir.mkdir(parents=True, exist_ok=True)

    scripts_written = []
    for product_type, product_info in PRODUCTS.items():
        product_id = product_type.replace("L2__", "").replace("___", "")
        band_map = {"SO2": "SO2_column_number_density",
                    "NO2": "NO2_column_number_density_troposphere",
                    "CH4": "CH4_column_volume_mixing_ratio_dry_air"}
        band = band_map.get(product_info["name"], product_info["name"].lower())

        for zone_name in ["A", "B", "E"]:
            script = GEE_SCRIPT_TEMPLATE.format(
                product_name=product_info["name"],
                product_id=product_id,
                geojson_bbox=f'"{ZONES[zone_name]}"',
                start="2023-01-01",
                end="2023-12-31",
                band=band,
                zone=zone_name,
            )
            script_path = gee_dir / f"s5p_{product_info['name'].lower()}_zone{zone_name}.js"
            with open(script_path, "w") as f:
                f.write(script)
            scripts_written.append(script_path)

    log.info(f"Wrote {len(scripts_written)} GEE scripts to {gee_dir}")
    return scripts_written


def build_placeholder_records() -> list[dict]:
    """
    Build data-acquisition-status records documenting what's needed.
    These show up in the map as 'data needed' markers at zone centroids.
    """
    zone_centers = {
        "A": (37.5, -108.0),
        "B": (32.0, -118.5),
        "E": (37.0, 140.0),
    }

    records = []
    for product_type, product_info in PRODUCTS.items():
        for zone_name, (lat, lon) in zone_centers.items():
            notes = (
                f"Sentinel-5P {product_info['name']} | Zone {zone_name} | "
                f"Interest: {product_info['interest']} | "
                f"Status: GEE script generated — run via Google Earth Engine or "
                f"sentinelsat API (requires free Copernicus account)"
            )
            try:
                rec = make_record(
                    layer=LAYER,
                    lat=lat,
                    lon=lon,
                    confidence=2,
                    category=CATEGORY,
                    source="ESA Sentinel-5P TROPOMI (acquisition pending)",
                    notes=notes,
                    extra={
                        "product": product_info["name"],
                        "zone": zone_name,
                        "status": "acquisition_pending",
                        "gee_collection": f"COPERNICUS/S5P/NRTI/L3_{product_type.replace('L2__', '').replace('___', '')}",
                    },
                )
                records.append(rec)
            except ValueError:
                continue

    return records


def main():
    log.info("=== fetch_sentinel5p.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Try API if credentials available
    if COPERNICUS_USER and COPERNICUS_PASS:
        log.info("Copernicus credentials found — attempting sentinelsat API…")
        for product_type, product_info in PRODUCTS.items():
            for zone_name, zone_wkt in ZONES.items():
                try_sentinelsat_api(product_type, product_info, zone_name, zone_wkt)
    else:
        log.info(
            "Copernicus credentials not set.\n"
            "  To enable: add COPERNICUS_USER and COPERNICUS_PASS to .env\n"
            "  Register free at: https://scihub.copernicus.eu/dhus/#/self-registration\n"
            "  Alternative: use Google Earth Engine (no download required):"
        )

    # Generate GEE scripts regardless
    gee_scripts = generate_gee_scripts()
    log.info(f"GEE scripts generated in {RAW_DIR / 'gee_scripts'}")
    log.info("  To run: paste scripts at https://code.earthengine.google.com/")

    # Write placeholder records (marks zones as pending in the map)
    records = build_placeholder_records()
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Wrote {len(records)} acquisition-status records → {OUT_PATH}")
    log.info(
        "\nOnce GEE or sentinelsat data is available, place exported GeoTIFF/CSV\n"
        "in data/manual/ and run process/geocode_manual.py to ingest anomaly points."
    )


if __name__ == "__main__":
    main()

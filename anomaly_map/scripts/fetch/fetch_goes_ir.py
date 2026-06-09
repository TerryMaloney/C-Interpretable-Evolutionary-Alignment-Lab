"""
Fetch NOAA GOES IR imagery for atmospheric gravity wave detection.

Source: NOAA GOES-East (16) and GOES-West (18)
AWS Open Data: s3://noaa-goes16/ and s3://noaa-goes18/
Browse: https://registry.opendata.aws/noaa-goes/

Physics basis: Fluid dynamics (atmospheric). Fast-moving objects, explosions,
and energy releases generate atmospheric gravity waves — concentric ripple
patterns visible in satellite IR/water vapor imagery.

Detection method:
  - Bands 8/9/10 (water vapor, 6.2/6.9/7.3μm) for gravity wave detection
  - Requires time-lapse animation and image differencing
  - Look for: concentric rings, expanding arcs, anomalous wave fronts
    NOT correlated with weather, rocket launches, or explosions

Analysis target:
  - Wave patterns with no NOTAM/weather correlation
  - Over or near Zones A, B during high UAP report periods
  - Cross-reference with USGS seismic catalog (gravity waves can precede quakes)

Archive: GOES-16 from 2017; GOES-18 from 2022

Last verified: 2026-06-09

Dependencies: goes2go, xarray, netCDF4

Note: Raster pipeline — significantly more complex than other layers.
      This script sets up the framework; full gravity wave detection
      requires interactive time-lapse analysis. Lower priority than 18-21.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, get_logger,
    make_record, records_to_geojson, save_geojson,
)

log = get_logger("fetch_goes_ir")

LAYER = "goes_gravity_waves"
CONFIDENCE = 2
CATEGORY = "atmospheric"

RAW_DIR = RAW_DATA_DIR / "goes_ir"
OUT_PATH = PROCESSED_DATA_DIR / "goes_gravity_waves.geojson"

# Bands optimal for gravity wave detection
WATER_VAPOR_BANDS = {
    "C08": "Upper-level WV (6.2μm) — stratospheric gravity waves",
    "C09": "Mid-level WV (6.9μm) — tropospheric waves",
    "C10": "Lower-level WV (7.3μm) — lower tropospheric",
}

# Known atmospheric gravity wave events (from published research)
KNOWN_GRAVITY_WAVE_EVENTS = [
    {
        "name": "Tonga Eruption Lamb Wave (global)",
        "lat": -20.54, "lon": -175.39,
        "datetime": "2022-01-15T04:15:00Z",
        "notes": (
            "Hunga Tonga eruption atmospheric Lamb wave propagated globally. "
            "Detected in GOES imagery as concentric rings expanding from source. "
            "Calibration event — useful for tuning gravity wave detection algorithm."
        ),
        "source": "NOAA GOES-17 / published research",
        "confidence": 5,
    },
    {
        "name": "Chelyabinsk Meteor Atmospheric Wave",
        "lat": 54.8, "lon": 61.1,
        "datetime": "2013-02-15T03:20:33Z",
        "notes": (
            "Chelyabinsk meteor entry generated atmospheric pressure wave. "
            "Detected in Meteosat IR imagery. ~500kt explosion equivalent. "
            "Calibration event for high-energy atmospheric disturbance signature."
        ),
        "source": "Meteosat / Himawari (pre-GOES-R era) imagery",
        "confidence": 5,
    },
    {
        "name": "Beirut Explosion Atmospheric Wave",
        "lat": 33.90, "lon": 35.52,
        "datetime": "2020-08-04T15:08:00Z",
        "notes": (
            "Beirut port explosion atmospheric wave clearly visible in Meteosat-11 WV imagery. "
            "~0.5kt TNT. Demonstrates detection threshold for chemical explosion class. "
            "Calibration: any unexplained event of this magnitude should be detectable."
        ),
        "source": "Meteosat-11 / ESA Copernicus",
        "confidence": 5,
    },
]

# Zones for focused GOES analysis requests
ZONE_FOCUS = {
    "A": {"center_lat": 37.5, "center_lon": -108.0, "radius_deg": 5},
    "B": {"center_lat": 32.0, "center_lon": -118.5, "radius_deg": 4},
}

GEE_GOES_SCRIPT = """
// Google Earth Engine: GOES-16 water vapor time-lapse for gravity wave detection
// Run at: https://code.earthengine.google.com/

var zone = ee.Geometry.Rectangle([-121, 29, -116, 35]);  // Zone B
var startDate = '2023-06-01';
var endDate = '2023-06-08';

// Load GOES-16 ABI Band 8 (upper water vapor)
var goes = ee.ImageCollection('NOAA/GOES/16/MCMIPC')
  .filterDate(startDate, endDate)
  .filterBounds(zone)
  .select('CMI_C08');

// Create time-lapse animation
var visParams = {
  min: 180,
  max: 280,
  palette: ['black', 'blue', 'cyan', 'white']
};

// Export animation for manual inspection
var frames = goes.map(function(img) {
  return img.clip(zone).visualize(visParams);
});

Export.video.toDrive({
  collection: frames,
  description: 'GOES16_WV_ZoneB_timelapse',
  framesPerSecond: 4,
  dimensions: 720
});

print('Images in collection:', goes.size());
"""


def setup_goes2go_config():
    """Check goes2go availability and print usage instructions."""
    try:
        import goes2go
        log.info("goes2go available — ready for GOES data download")
        return True
    except ImportError:
        log.info("goes2go not installed. Install with: pip install goes2go")
        return False


def build_calibration_records() -> list[dict]:
    """Build records from known gravity wave events (calibration set)."""
    records = []
    for event in KNOWN_GRAVITY_WAVE_EVENTS:
        try:
            rec = make_record(
                layer=LAYER,
                lat=event["lat"],
                lon=event["lon"],
                datetime_str=event.get("datetime"),
                confidence=event["confidence"],
                category=CATEGORY,
                source=event["source"],
                notes=f"[CALIBRATION EVENT] {event['name']} | {event['notes']}",
                extra={
                    "event_name": event["name"],
                    "is_calibration": True,
                    "detection_type": "atmospheric_gravity_wave",
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue
    return records


def build_zone_placeholder_records() -> list[dict]:
    """Mark analysis zones as pending gravity wave scan."""
    records = []
    for zone_id, zone in ZONE_FOCUS.items():
        try:
            rec = make_record(
                layer=LAYER,
                lat=zone["center_lat"],
                lon=zone["center_lon"],
                confidence=1,
                category=CATEGORY,
                source="NOAA GOES-16/18 (scan pending)",
                notes=(
                    f"Zone {zone_id} — GOES water vapor scan pending. "
                    f"Use goes2go or GEE script to download Band 8/9/10 imagery. "
                    f"Analyze time-lapse for unexplained concentric wave patterns. "
                    f"GEE script written to data/raw/goes_ir/gee_script.js"
                ),
                extra={
                    "zone": zone_id,
                    "status": "scan_pending",
                    "bands_to_analyze": list(WATER_VAPOR_BANDS.keys()),
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue
    return records


def write_gee_script():
    """Write GEE script for manual cloud-based analysis."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    script_path = RAW_DIR / "gee_goes16_gravity_waves.js"
    with open(script_path, "w") as f:
        f.write(GEE_GOES_SCRIPT)
    log.info(f"GEE script written to {script_path}")
    log.info("  Run at: https://code.earthengine.google.com/")


def main():
    log.info("=== fetch_goes_ir.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    goes2go_available = setup_goes2go_config()
    write_gee_script()

    calibration_records = build_calibration_records()
    placeholder_records = build_zone_placeholder_records()
    all_records = calibration_records + placeholder_records

    log.info(f"Total GOES records: {len(all_records)} ({len(calibration_records)} calibration events)")

    gj = records_to_geojson(all_records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")

    log.info(
        "\nFor GOES gravity wave analysis:\n"
        "  Option 1 (Cloud): Paste GEE script from data/raw/goes_ir/gee_goes16_gravity_waves.js\n"
        "                    at https://code.earthengine.google.com/\n"
        "  Option 2 (Local): Install goes2go (pip install goes2go), then:\n"
        "    from goes2go import GOES\n"
        "    G = GOES(satellite=16, product='ABI-L2-CMIPF', domain='C')\n"
        "    df = G.timerange('2023-01-01', '2023-01-02')\n"
        "  Band 8 (C08) = best for gravity wave detection\n"
        "  Look for: concentric rings in time-lapse not matching weather"
    )


if __name__ == "__main__":
    main()

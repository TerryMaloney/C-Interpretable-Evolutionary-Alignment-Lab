"""
Fetch NOAA VIIRS Nighttime Lights — industrial activity masking layer.

Source: NOAA National Centers for Environmental Information (NCEI)
Annual composites: https://www.ngdc.noaa.gov/eog/viirs/download_dnb_composites.html
Archive: 2012–present (monthly + annual composites)

Purpose: INDUSTRIAL/POPULATION ACTIVITY MASK
  Used to distinguish anomalous thermal events from industrial activity.
  High nighttime light = industrial area = thermal/EM anomalies expected.
  Low nighttime light + thermal anomaly = more analytically interesting.

Primary use cases:
  1. Filter FIRMS thermal anomalies: mask detections in high-light areas
     (oil refineries, smelters, flares produce persistent FIRMS detections)
  2. Population density proxy: complement Census data for urban/rural correction
  3. Industrial corridor mapping: identify known industrial vs wilderness areas

Data products:
  - Monthly cloud-free composites (VNL v2.1): radiance in nW/cm²/sr
  - Annual composites available from 2012

Last verified: 2026-06-09

Output: Grid of high-light zones (industrial mask) as point records,
        plus known major industrial areas as manual annotations.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    RAW_DATA_DIR, PROCESSED_DATA_DIR, fetch_with_retry,
    get_logger, make_record, records_to_geojson, save_geojson, save_raw,
)

log = get_logger("fetch_nighttime_lights")

LAYER = "nighttime_lights"
CONFIDENCE = 5
CATEGORY = "mask"

RAW_DIR = RAW_DATA_DIR / "nighttime_lights"
OUT_PATH = PROCESSED_DATA_DIR / "nighttime_lights.geojson"

# NOAA EOG annual composite download URLs
# Format: VNL_v21_npp_{YEAR}_global_vcmslcfg_c{VERSION}_slcfg_cf_cvg.tif
NOAA_EOG_BASE = "https://eogdata.mines.edu/nighttime_light/annual/v21/"
NOAA_EOG_RECENT = f"{NOAA_EOG_BASE}2022/VNL_v21_npp_2022_global_vcmslcfg_c202303062300.average_masked.dat.tif.gz"

# Alternative: NASA Black Marble product (better quality, requires Earthdata login)
NASA_BLACK_MARBLE_BASE = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5000/VNP46A3/"

# Light threshold for industrial classification (nW/cm²/sr)
INDUSTRIAL_THRESHOLD = 50.0  # High urban/industrial
GRID_RESOLUTION = 0.5  # Degrees; aggregate at this scale for output size

# Known major industrial/oil-field zones where FIRMS detections are expected
KNOWN_INDUSTRIAL_ZONES = [
    {"name": "Permian Basin oil fields",        "lat": 31.9,  "lon": -103.1,
     "notes": "Largest US oil production; persistent gas flaring detectable by FIRMS"},
    {"name": "Eagle Ford Shale",                "lat": 28.5,  "lon": -99.2,
     "notes": "South Texas shale oil; gas flares produce FIRMS detections"},
    {"name": "Bakken Shale (North Dakota)",     "lat": 47.5,  "lon": -103.0,
     "notes": "Williston Basin oil field; high gas flaring"},
    {"name": "Gulf of Mexico platforms",        "lat": 28.0,  "lon": -90.0,
     "notes": "Offshore platform flaring and lighting — expected FIRMS"},
    {"name": "Athabasca Oil Sands",             "lat": 57.0,  "lon": -111.5,
     "notes": "Alberta oil sands — massive industrial thermal footprint"},
    {"name": "Four Corners coal plants",        "lat": 36.8,  "lon": -108.5,
     "notes": "San Juan/Four Corners power plants — industrial heat signature"},
    {"name": "Houston Ship Channel refineries", "lat": 29.8,  "lon": -95.1,
     "notes": "Largest US refinery complex — persistent industrial heat"},
    {"name": "Los Angeles basin industrial",    "lat": 33.9,  "lon": -118.1,
     "notes": "Heavy industrial zone — LA port, refineries, manufacturing"},
    {"name": "Chicago/Gary steel mills",        "lat": 41.6,  "lon": -87.3,
     "notes": "Steel production — significant industrial thermal signature"},
    {"name": "Pittsburgh steel corridor",       "lat": 40.4,  "lon": -80.0,
     "notes": "Allegheny industrial corridor — expected industrial detections"},
    # International
    {"name": "Siberian gas flaring (Russia)",   "lat": 63.0,  "lon": 76.0,
     "notes": "World's largest gas flaring zone — massive persistent FIRMS signal"},
    {"name": "Niger Delta gas flaring",         "lat": 5.5,   "lon": 6.0,
     "notes": "Nigeria oil production — extensive flaring"},
    {"name": "Persian Gulf oil fields",         "lat": 24.5,  "lon": 51.0,
     "notes": "Saudi/Kuwait/UAE oil production — widespread flaring"},
    {"name": "North Korea border (for absence)","lat": 40.0,  "lon": 127.0,
     "notes": "North Korea shows near-zero nighttime light — anomalies here ARE anomalous"},
]


def download_viirs_tif() -> Path | None:
    """Download NOAA EOG VIIRS annual composite."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    gz_path = RAW_DIR / "vnl_annual.tif.gz"
    tif_path = RAW_DIR / "vnl_annual.tif"

    if tif_path.exists():
        log.info(f"TIF already present: {tif_path}")
        return tif_path

    log.info(f"Downloading VIIRS nighttime lights TIF (~2GB)…")
    log.info("  This is a large file. Consider downloading manually from:")
    log.info("  https://www.ngdc.noaa.gov/eog/viirs/download_dnb_composites.html")

    try:
        resp = fetch_with_retry(NOAA_EOG_RECENT, stream=True, logger=log)
        with open(gz_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        log.info(f"Downloaded to {gz_path}")

        import gzip, shutil
        with gzip.open(gz_path, "rb") as f_in:
            with open(tif_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        log.info(f"Extracted to {tif_path}")
        return tif_path
    except Exception as exc:
        log.warning(f"Download failed: {exc}")
        return None


def extract_high_light_zones(tif_path: Path) -> list[dict]:
    """Sample raster and extract high-light areas as industrial mask points."""
    try:
        import rasterio
        from rasterio.transform import xy
        from pyproj import Transformer
    except ImportError:
        log.error("rasterio required: pip install rasterio")
        return []

    log.info(f"Extracting industrial zones from {tif_path}…")
    records = []

    with rasterio.open(tif_path) as src:
        data = src.read(1).astype(float)
        nodata = src.nodata
        if nodata is not None:
            data[data == nodata] = np.nan

        log.info(f"Raster: {data.shape}, CRS: {src.crs}")
        high_light_mask = data > INDUSTRIAL_THRESHOLD
        rows, cols = np.where(high_light_mask)
        log.info(f"High-light pixels (>{INDUSTRIAL_THRESHOLD} nW/cm²/sr): {len(rows):,}")

        # Aggressive subsampling — we only need grid-level coverage
        STEP = 50
        rows, cols = rows[::STEP], cols[::STEP]
        log.info(f"After 1/{STEP} sampling: {len(rows):,} points")

        xs, ys = xy(src.transform, rows, cols)
        if src.crs and src.crs.to_epsg() != 4326:
            t = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
            lons, lats = t.transform(xs, ys)
        else:
            lons, lats = xs, ys

        for lat, lon, r, c in zip(lats, lons, rows, cols):
            val = float(data[r, c])
            try:
                rec = make_record(
                    layer=LAYER,
                    lat=lat,
                    lon=lon,
                    confidence=CONFIDENCE,
                    category=CATEGORY,
                    source="NOAA VIIRS DNB Annual Composite",
                    notes=f"Industrial/urban light: {val:.1f} nW/cm²/sr | MASK: expected EM/thermal detections",
                    extra={"radiance_nw_cm2_sr": round(val, 2), "mask_type": "industrial"},
                )
                records.append(rec)
            except ValueError:
                continue

    log.info(f"Extracted {len(records):,} industrial zone records")
    return records


def build_manual_records() -> list[dict]:
    records = []
    for zone in KNOWN_INDUSTRIAL_ZONES:
        try:
            rec = make_record(
                layer=LAYER,
                lat=zone["lat"],
                lon=zone["lon"],
                confidence=CONFIDENCE,
                category=CATEGORY,
                source="Manual industrial zone annotation",
                notes=f"[INDUSTRIAL MASK] {zone['name']} | {zone['notes']}",
                extra={
                    "zone_name": zone["name"],
                    "mask_type": "industrial_manual",
                    "mask_function": "Expected FIRMS/EM detections — do not flag as anomalous",
                },
            )
            records.append(rec)
        except (ValueError, TypeError):
            continue
    log.info(f"Built {len(records)} manual industrial zone records")
    return records


def main():
    log.info("=== fetch_nighttime_lights.py ===")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    records = build_manual_records()

    tif_path = download_viirs_tif()
    if tif_path:
        raster_records = extract_high_light_zones(tif_path)
        records.extend(raster_records)
    else:
        log.info("Using manual industrial zones only (raster download failed)")
        log.info(
            "  For full industrial mask, download VIIRS annual composite from:\n"
            "  https://www.ngdc.noaa.gov/eog/viirs/download_dnb_composites.html\n"
            f"  Place at: {RAW_DIR / 'vnl_annual.tif'} and re-run"
        )

    log.info(f"Total nighttime light records: {len(records):,}")
    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    log.info(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()

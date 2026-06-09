"""
Download USGS North American Magnetic Anomaly Grid (NAMAG).

Source: USGS Geomagnetism Program
Main page: https://mrdata.usgs.gov/magnetic/
Data catalog: https://data.usgs.gov/datacatalog/data/USGS:619a9a3ad34eb622f692f961

The primary dataset is a GeoTIFF raster (~500MB). This script:
1. Downloads the raster to data/raw/usgs_magnetic/
2. Samples the raster at a grid to extract high-anomaly zones (|anomaly| > 1.5 SD)
3. Outputs those zones as point records to data/processed/usgs_magnetic_summary.geojson

Last verified: 2026-06-09

Note: Full GeoTIFF download requires stable connection (~500MB).
If auto-download fails, manually place NAMAG.tif in data/raw/usgs_magnetic/
and re-run — the script will skip the download step.
"""

import sys
from pathlib import Path

import numpy as np

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

log = get_logger("fetch_usgs_magnetic")

LAYER = "usgs_magnetic"
CONFIDENCE = 5
CATEGORY = "geophysical"

RAW_DIR = RAW_DATA_DIR / "usgs_magnetic"
TIF_PATH = RAW_DIR / "NAMAG.tif"
OUT_PATH = PROCESSED_DATA_DIR / "usgs_magnetic_summary.geojson"

# Known public GeoTIFF endpoints (check USGS ScienceBase for current URLs)
DOWNLOAD_URLS = [
    "https://pubs.usgs.gov/of/2002/ofr-02-414/data/namag.zip",
    "https://mrdata.usgs.gov/magnetic/namag.zip",
]

ANOMALY_THRESHOLD_SD = 1.5  # Extract zones where |anomaly| > N standard deviations
SAMPLE_STEP = 10            # Sample every Nth pixel to reduce output size


def download_raster():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if TIF_PATH.exists():
        log.info(f"TIF already present at {TIF_PATH}, skipping download")
        return True

    zip_path = RAW_DIR / "namag.zip"
    for url in DOWNLOAD_URLS:
        log.info(f"Attempting download from {url}")
        try:
            resp = fetch_with_retry(url, stream=True, logger=log)
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
            log.info(f"Downloaded to {zip_path}")

            import zipfile
            with zipfile.ZipFile(zip_path, "r") as zf:
                tif_names = [n for n in zf.namelist() if n.lower().endswith(".tif")]
                if tif_names:
                    zf.extract(tif_names[0], RAW_DIR)
                    extracted = RAW_DIR / tif_names[0]
                    extracted.rename(TIF_PATH)
                    log.info(f"Extracted TIF to {TIF_PATH}")
                    return True
        except Exception as exc:
            log.warning(f"Download attempt failed: {exc}")

    log.error(
        "Automatic download failed. Manual steps:\n"
        "  1. Visit https://mrdata.usgs.gov/magnetic/\n"
        "  2. Download the North American Magnetic Anomaly Grid GeoTIFF\n"
        f"  3. Place at {TIF_PATH}"
    )
    return False


def extract_anomaly_zones() -> list[dict]:
    """Sample raster and return records for high-anomaly zones."""
    try:
        import rasterio
        from rasterio.transform import xy
    except ImportError:
        log.error("rasterio not installed. Run: pip install rasterio")
        return []

    if not TIF_PATH.exists():
        log.warning(f"Raster not found at {TIF_PATH}. Run download first.")
        return []

    log.info(f"Reading raster from {TIF_PATH}…")
    records = []

    with rasterio.open(TIF_PATH) as src:
        data = src.read(1).astype(float)
        nodata = src.nodata
        if nodata is not None:
            data[data == nodata] = np.nan

        valid = data[~np.isnan(data)]
        mean_val = np.nanmean(valid)
        std_val = np.nanstd(valid)
        threshold = ANOMALY_THRESHOLD_SD * std_val

        log.info(f"Raster stats: mean={mean_val:.1f}, std={std_val:.1f}, threshold=±{threshold:.1f}")
        log.info(f"Raster shape: {data.shape}, CRS: {src.crs}")

        rows, cols = np.where(np.abs(data - mean_val) > threshold)
        log.info(f"High-anomaly pixels (before sampling): {len(rows):,}")

        # Subsample to keep output manageable
        mask = np.arange(len(rows)) % SAMPLE_STEP == 0
        rows, cols = rows[mask], cols[mask]
        log.info(f"After 1/{SAMPLE_STEP} sampling: {len(rows):,} points")

        xs, ys = xy(src.transform, rows, cols)
        # Transform to WGS84 if needed
        from pyproj import Transformer
        if src.crs and src.crs.to_epsg() != 4326:
            transformer = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
            lons, lats = transformer.transform(xs, ys)
        else:
            lons, lats = xs, ys

        for lat, lon, row_idx, col_idx in zip(lats, lons, rows, cols):
            anomaly_val = float(data[row_idx, col_idx])
            try:
                rec = make_record(
                    layer=LAYER,
                    lat=lat,
                    lon=lon,
                    confidence=CONFIDENCE,
                    category=CATEGORY,
                    source="USGS NAMAG",
                    notes=f"Magnetic anomaly: {anomaly_val:.1f} nT (>{ANOMALY_THRESHOLD_SD}σ)",
                    extra={"anomaly_nt": round(anomaly_val, 2)},
                )
                records.append(rec)
            except ValueError:
                continue

    log.info(f"Extracted {len(records):,} anomaly zone records")
    return records


def main():
    log.info("=== fetch_usgs_magnetic.py ===")
    downloaded = download_raster()
    if not downloaded and not TIF_PATH.exists():
        log.warning("Skipping raster extraction — no TIF available")
        return

    records = extract_anomaly_zones()
    if records:
        gj = records_to_geojson(records)
        save_geojson(gj, OUT_PATH)
        log.info(f"Saved {len(records):,} records → {OUT_PATH}")
    else:
        log.warning("No records extracted — check raster file and dependencies")


if __name__ == "__main__":
    main()

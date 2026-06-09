"""
Fetch USGS Geologic Radon Potential Map data.

Source: US Geological Survey
Main page: https://www.usgs.gov/data/geologic-radon-potential-map-united-states
Original report: USGS OFR 93-292

The dataset is a county/geologic province level GIS database.
This script downloads the shapefile and converts to point records
(county centroids) weighted by radon potential class.

Radon potential classes:
  High (>4 pCi/L predicted average): Class 1
  Moderate (2-4 pCi/L): Class 2
  Low (<2 pCi/L): Class 3

Last verified: 2026-06-09
"""

import sys
from pathlib import Path

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

log = get_logger("fetch_usgs_radon")

LAYER = "usgs_radon"
CONFIDENCE = 4
CATEGORY = "geophysical"

RAW_DIR = RAW_DATA_DIR / "usgs_radon"
OUT_PATH = PROCESSED_DATA_DIR / "usgs_radon.geojson"

# USGS radon potential shapefile (zip)
RADON_URL = "https://pubs.usgs.gov/of/1993/292/ofr93-292.zip"
# Alternative: ScienceBase catalog item
RADON_URL_ALT = "https://www.sciencebase.gov/catalog/file/get/5d09f07be4b0b64b38fba4d2"

RADON_CLASS_LABELS = {
    1: "High (>4 pCi/L)",
    2: "Moderate (2-4 pCi/L)",
    3: "Low (<2 pCi/L)",
}

# Confidence boost for high radon areas (analytically relevant)
RADON_CONFIDENCE_MAP = {1: 4, 2: 3, 3: 2}


def download_shapefile() -> Path | None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / "usgs_radon.zip"

    if zip_path.exists():
        log.info(f"Zip already present at {zip_path}")
        return zip_path

    for url in [RADON_URL, RADON_URL_ALT]:
        log.info(f"Attempting download: {url}")
        try:
            resp = fetch_with_retry(url, stream=True, logger=log)
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
            log.info(f"Downloaded to {zip_path}")
            return zip_path
        except Exception as exc:
            log.warning(f"Failed: {exc}")

    log.error(
        "Could not download USGS radon shapefile.\n"
        "Manual download: https://www.usgs.gov/data/geologic-radon-potential-map-united-states\n"
        f"Place zip at: {zip_path}"
    )
    return None


def extract_and_process(zip_path: Path) -> list[dict]:
    try:
        import geopandas as gpd
    except ImportError:
        log.error("geopandas required: pip install geopandas")
        return []

    import zipfile

    # Extract shapefile
    extract_dir = RAW_DIR / "extracted"
    extract_dir.mkdir(exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
    except Exception as exc:
        log.error(f"Extraction failed: {exc}")
        return []

    # Find shapefile
    shp_files = list(extract_dir.rglob("*.shp"))
    if not shp_files:
        log.error(f"No .shp file found in {extract_dir}")
        return []

    shp_path = shp_files[0]
    log.info(f"Reading shapefile: {shp_path}")

    try:
        gdf = gpd.read_file(shp_path)
        gdf = gdf.to_crs("EPSG:4326")
        log.info(f"Loaded {len(gdf)} features, columns: {list(gdf.columns)}")
    except Exception as exc:
        log.error(f"Failed to read shapefile: {exc}")
        return []

    # Find radon class column
    radon_col = next(
        (c for c in gdf.columns if "radon" in c.lower() or "rn" in c.lower() or "class" in c.lower()),
        None,
    )
    state_col = next((c for c in gdf.columns if "state" in c.lower() or "stateabb" in c.lower()), None)
    county_col = next((c for c in gdf.columns if "county" in c.lower() or "name" in c.lower()), None)

    records = []
    for _, row in gdf.iterrows():
        try:
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            centroid = geom.centroid
            lat, lon = centroid.y, centroid.x

            radon_class = int(row[radon_col]) if radon_col and row[radon_col] is not None else None
            state = str(row[state_col]) if state_col else ""
            county = str(row[county_col]) if county_col else ""

            label = RADON_CLASS_LABELS.get(radon_class, "Unknown")
            conf = RADON_CONFIDENCE_MAP.get(radon_class, CONFIDENCE)

            notes = f"Radon potential: {label}"
            if county:
                notes += f" | {county}"
            if state:
                notes += f", {state}"

            rec = make_record(
                layer=LAYER,
                lat=lat,
                lon=lon,
                confidence=conf,
                category=CATEGORY,
                source="USGS OFR 93-292",
                notes=notes,
                extra={
                    "radon_class": radon_class,
                    "radon_label": label,
                    "state": state,
                    "county": county,
                },
            )
            records.append(rec)
        except Exception:
            continue

    log.info(f"Extracted {len(records):,} radon records")
    return records


def main():
    log.info("=== fetch_usgs_radon.py ===")
    zip_path = download_shapefile()
    if zip_path is None:
        return

    records = extract_and_process(zip_path)
    if records:
        gj = records_to_geojson(records)
        save_geojson(gj, OUT_PATH)
        log.info(f"Saved {len(records):,} records → {OUT_PATH}")


if __name__ == "__main__":
    main()

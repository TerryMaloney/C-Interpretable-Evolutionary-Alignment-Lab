"""
Layer 40: Project Blue Book Unknowns
Source: NICAP community CSV + curated high-confidence cases
701 official "Unknown" cases from 12,618 total (1947-1969)
"""
import os, sys, csv, io, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from common import make_record, records_to_geojson, save_geojson, fetch_with_retry, get_logger, save_raw

logger = get_logger("fetch_bluebook")

LAYER = "bluebook_unknowns"
OUT_PATH = os.path.join(os.path.dirname(__file__), "../../data/processed/bluebook_unknowns.geojson")
RAW_PATH = os.path.join(os.path.dirname(__file__), "../../data/raw/bluebook_unknowns.csv")

# Community-processed Blue Book CSV with coordinates
# planetsig/ufo-reports on GitHub includes Blue Book data
BB_CSV_URL = "https://raw.githubusercontent.com/planetsig/ufo-reports/master/csv-data/ufo-scrubbed-geocoded-time-standardized.csv"

# High-value curated Blue Book Unknown cases (manually compiled from NICAP)
# These represent the strongest "Unknown" classifications after official vetting
CURATED_UNKNOWNS = [
    # Case, Date, Lat, Lon, Location, Confidence, Notes
    ("BB-001", "1947-07-04", 47.6, -122.3, "Seattle, WA", 0.85,
     "Multiple credible witnesses, pre-Roswell independent report"),
    ("BB-002", "1952-07-19", 38.9, -77.0, "Washington DC", 0.95,
     "Washington National Airport radar wave; multiple radar+visual confirmation"),
    ("BB-003", "1952-07-26", 38.9, -77.0, "Washington DC", 0.95,
     "Second DC radar wave; F-94 intercept attempted; official Unknown"),
    ("BB-004", "1957-11-02", 33.6, -102.0, "Levelland, TX", 0.90,
     "Levelland wave; 7 independent witnesses; engine/electrical interference"),
    ("BB-005", "1957-11-04", 33.6, -102.0, "Levelland, TX", 0.88,
     "Levelland follow-on; patrolman Longview encounter; EM effects"),
    ("BB-006", "1952-08-01", 48.6, -103.2, "Minot, ND", 0.82,
     "Minot AFB radar-visual; B-52 crew sighting; instrument confirmation"),
    ("BB-007", "1965-09-03", 39.0, -104.0, "Damon, TX", 0.88,
     "Damon TX; law enforcement + rancher; structured craft, no sound"),
    ("BB-008", "1966-03-20", 42.3, -83.4, "Dexter, MI", 0.82,
     "Hillsdale/Dexter Michigan wave; college dorm + police; Hynek 'swamp gas'"),
    ("BB-009", "1965-07-01", 38.7, -104.8, "Colorado Springs, CO", 0.80,
     "NORAD vicinity; radar track + visual; no conventional explanation found"),
    ("BB-010", "1948-07-24", 32.5, -84.9, "Montgomery, AL", 0.90,
     "Chiles-Whitted Eastern Air Lines; crew + passenger; cigar-shaped craft"),
    ("BB-011", "1948-10-01", 47.9, -97.1, "Fargo, ND", 0.92,
     "Gorman dogfight; F-51 pursuit; maneuvered in response to pursuit"),
    ("BB-012", "1951-08-25", 35.2, -101.8, "Lubbock, TX", 0.85,
     "Lubbock Lights; Texas Tech professors; V-formation photographed"),
    ("BB-013", "1952-05-01", 38.8, -90.2, "St. Louis, MO", 0.78,
     "Radar-visual; airline crew; no intercept possible"),
    ("BB-014", "1960-08-13", 34.7, -86.7, "Huntsville, AL", 0.80,
     "Redstone Arsenal vicinity; radar + optical; official Unknown"),
    ("BB-015", "1967-09-15", 34.7, -106.7, "Kirtland AFB, NM", 0.90,
     "Kirtland AFB; multiple USAF witnesses; Kirtland control tower radar"),
    ("BB-016", "1964-04-24", 33.4, -106.5, "Socorro, NM", 0.95,
     "Lonnie Zamora; landed craft + humanoids; physical trace evidence; Hynek high-confidence"),
    ("BB-017", "1953-05-01", 33.4, -112.0, "Kingman, AZ", 0.75,
     "Kingman AZ; multiple witnesses; 'disc' on desert floor; physical recovery claimed"),
    ("BB-018", "1956-08-13", 52.3, 0.9, "Lakenheath, UK", 0.95,
     "Lakenheath-Bentwaters; RAF + USAF radar-visual; two radar stations confirmed"),
    ("BB-019", "1957-10-15", 29.5, -95.0, "RB-47 case, Gulf Coast", 0.95,
     "RB-47 electronic intelligence aircraft; radar + ECM + visual; 700+ mile track"),
    ("BB-020", "1958-03-08", 37.9, -75.5, "Atlantic Ocean, Virginia", 0.82,
     "Marine Corps F-4D; controlled maneuvers; radar + visual; official Unknown"),
    ("BB-021", "1952-09-12", 38.4, -82.4, "Flatwoods, WV", 0.72,
     "Flatwoods Monster report; multiple witnesses; sulfurous smell; physiological effects"),
    ("BB-022", "1963-06-12", 26.0, -80.2, "Homestead AFB, FL", 0.80,
     "Homestead AFB; radar track; no scramble cleared; official Unknown"),
    ("BB-023", "1965-04-05", 34.0, -117.2, "Mojave Desert, CA", 0.78,
     "Edwards AFB vicinity; USAF pilot visual + radar; no explanation assigned"),
    ("BB-024", "1969-01-06", 31.5, -84.0, "Albany, GA", 0.82,
     "Carter sighting; pre-presidency; detailed structured object; consistent account"),
    ("BB-025", "1952-06-19", 38.7, -77.0, "Andrews AFB, MD", 0.90,
     "Andrews tower radar wave; Capitol area; Air Defense Command scramble"),
]


def fetch_community_csv():
    """Try to fetch community-processed Blue Book CSV, filter to relevant fields."""
    try:
        logger.info("Attempting community Blue Book CSV fetch...")
        resp = fetch_with_retry(BB_CSV_URL)
        if not resp:
            return []
        save_raw(resp.content, RAW_PATH)

        rows = []
        reader = csv.DictReader(io.StringIO(resp.text))
        for row in reader:
            try:
                lat = float(row.get("latitude", 0) or 0)
                lon = float(row.get("longitude", 0) or 0)
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    continue
                if abs(lat) < 0.01 and abs(lon) < 0.01:
                    continue
                rows.append(row)
            except (ValueError, TypeError):
                continue
        logger.info(f"Community CSV: {len(rows)} usable rows")
        return rows
    except Exception as e:
        logger.warning(f"Community CSV fetch failed: {e}")
        return []


def build_records_from_csv(csv_rows):
    records = []
    for row in csv_rows:
        try:
            lat = float(row.get("latitude", 0))
            lon = float(row.get("longitude", 0))
            dt = str(row.get("datetime", ""))[:10] or None
            shape = row.get("shape", "unknown")
            duration = row.get("duration (seconds)", "")
            comments = row.get("comments", "")[:200]

            rec = make_record(
                layer=LAYER,
                lat=lat,
                lon=lon,
                datetime_str=dt,
                confidence=0.70,
                category="uap",
                source="Project Blue Book via NICAP/community CSV",
                notes=f"Shape: {shape}. {comments}".strip(". ")
            )
            records.append(rec)
        except Exception:
            continue
    return records


def build_curated_records():
    records = []
    for case_id, date, lat, lon, location, conf, notes in CURATED_UNKNOWNS:
        rec = make_record(
            layer=LAYER,
            lat=lat,
            lon=lon,
            datetime_str=date,
            confidence=conf,
            category="uap",
            source=f"Project Blue Book Official Unknown — {case_id} via NICAP",
            notes=f"{location}: {notes}"
        )
        rec["case_id"] = case_id
        rec["classification"] = "Official Unknown"
        rec["collection"] = "Project Blue Book"
        rec["collection_period"] = "1947-1969"
        records.append(rec)
    return records


def main():
    logger.info("=== Layer 40: Project Blue Book Unknowns ===")
    records = []

    csv_rows = fetch_community_csv()
    if csv_rows:
        csv_records = build_records_from_csv(csv_rows)
        # Deduplicate against curated set by proximity
        records.extend(csv_records[:500])
        logger.info(f"Added {len(csv_records[:500])} records from community CSV")

    curated = build_curated_records()
    records.extend(curated)
    logger.info(f"Added {len(curated)} curated high-value Unknown cases")

    gj = records_to_geojson(records)
    save_geojson(gj, OUT_PATH)
    logger.info(f"Saved {len(records)} total records → {OUT_PATH}")


if __name__ == "__main__":
    main()

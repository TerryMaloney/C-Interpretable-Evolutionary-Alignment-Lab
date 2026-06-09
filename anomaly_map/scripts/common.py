"""
Shared utilities for the Anomaly Correlation Map pipeline.
All scripts import from here for consistent schema enforcement and I/O.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# Project root is two levels up from this file (anomaly_map/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", PROJECT_ROOT / "data" / "raw"))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", PROJECT_ROOT / "data" / "processed"))
MANUAL_DATA_DIR = PROJECT_ROOT / "data" / "manual"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output"))
REGISTRY_PATH = PROJECT_ROOT / "data" / "layer_registry.json"

REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.0"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def load_registry() -> dict:
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def make_record(
    layer: str,
    lat: float,
    lon: float,
    datetime_str: Optional[str] = None,
    confidence: Optional[int] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    notes: Optional[str] = None,
    extra: Optional[dict] = None,
) -> dict:
    """Build a standard schema record. Raises if lat/lon invalid."""
    if lat is None or lon is None:
        raise ValueError(f"Record in layer '{layer}' missing lat/lon")
    lat, lon = float(lat), float(lon)
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")

    record = {
        "id": str(uuid.uuid4()),
        "layer": layer,
        "lat": lat,
        "lon": lon,
        "datetime": datetime_str,
        "confidence": confidence,
        "category": category,
        "source": source,
        "notes": notes,
    }
    if extra:
        record.update(extra)
    return record


def records_to_geojson(records: list[dict]) -> dict:
    """Convert list of standard records to GeoJSON FeatureCollection."""
    features = []
    for r in records:
        props = {k: v for k, v in r.items() if k not in ("lat", "lon")}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": props,
        })
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "record_count": len(features),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def save_geojson(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def save_raw(data: bytes | str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(path, mode) as f:
        f.write(data)


def fetch_with_retry(
    url: str,
    session: Optional[requests.Session] = None,
    max_retries: int = 4,
    params: Optional[dict] = None,
    stream: bool = False,
    logger: Optional[logging.Logger] = None,
) -> requests.Response:
    """GET with exponential backoff on failures."""
    log = logger or logging.getLogger("fetch")
    requester = session or requests
    delays = [2, 4, 8, 16]
    last_exc = None
    for attempt, delay in enumerate(delays[:max_retries], 1):
        try:
            resp = requester.get(url, params=params, stream=stream, timeout=60)
            resp.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            log.warning(f"Attempt {attempt} failed for {url}: {exc}. Retrying in {delay}s…")
            time.sleep(delay)
    raise RuntimeError(f"All {max_retries} attempts failed for {url}") from last_exc


def load_geojson(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)

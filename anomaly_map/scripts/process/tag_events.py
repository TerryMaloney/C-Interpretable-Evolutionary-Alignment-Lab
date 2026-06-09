"""
Event tagging and deduplication pass.

Two functions:
1. tag_events: Scan notes/source text for keyword-derived tags (secondary_effect_tags,
   physical_effect_score, confound_flags).
2. dedup_events: Assign incident_group_id and report_count to records that are
   spatially and temporally co-located (same event, multiple reports).

These enrichments are written back to the processed GeoJSON files.
They do NOT remove records — duplicates are kept but linked by incident_group_id.

Run after normalize_all.py:
  python scripts/process/tag_events.py
"""

import json
import math
import re
import uuid
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import get_logger, PROCESSED_DATA_DIR

log = get_logger("tag_events")

# ── Keyword tag definitions ─────────────────────────────────────────────────────

PHYSICAL_EFFECT_KEYWORDS = {
    # High-weight effects (2 pts each)
    "physical_evidence": ["physical trace", "burn mark", "landing trace", "impression",
                          "scorched", "radiation", "burns", "physical effects"],
    "radar_confirmation": ["radar", "flir", "infrared", "thermal", "ew track",
                           "radar lock", "radar contact", "adsb anomaly"],
    "EM_interference": ["engine stall", "electrical failure", "compass deviation",
                        "radio interference", "vehicle stall", "em effects",
                        "electromagnetic", "power failure"],
    # Medium-weight (1 pt each)
    "physiological": ["paralysis", "nausea", "headache", "burns", "rash",
                      "tingling", "disorientation", "amnesia", "paresthesia",
                      "conjunctivitis", "vision impairment"],
    "acoustic": ["no sound", "silent", "no sonic boom", "humming", "buzzing",
                 "infrasound", "acoustic"],
    "luminous_effects": ["pulsating", "color change", "strobing", "glow",
                         "luminous", "bright light", "illuminated"],
    "structured_craft": ["structured craft", "metallic", "triangular", "disc",
                         "sphere", "cigar", "hovering", "formation"],
}

CONFOUND_KEYWORDS = {
    "military_confound": ["military", "air force", "navy", "base", "restricted",
                          "classified", "nro", "cia", "dod", "pentagon",
                          "test range", "training area"],
    "industrial_confound": ["plant", "refinery", "factory", "industrial", "powerplant",
                            "chemical", "gas flare", "pipeline"],
    "population_bias": ["urban", "city", "downtown", "metropolitan", "highway",
                        "interstate", "airport nearby"],
    "reporting_bias": ["nuforc", "mufon", "bfro", "self-report", "anonymous",
                       "civilian report", "online submission"],
    "astronomical_confound": ["venus", "meteor", "shooting star", "satellite",
                               "balloon", "lantern", "aircraft light"],
    "coastal_confound": ["offshore", "coast", "coastal", "shoreline", "maritime",
                         "shipping lane"],
}

SECONDARY_EFFECT_TAGS = {
    "animal_reaction": ["animals", "cattle", "dogs barking", "birds fled",
                        "wildlife", "livestock"],
    "temporal_recurrence": ["again", "recurring", "same location", "multiple nights",
                             "previous report", "follow-on"],
    "multiple_witnesses": ["multiple witnesses", "independent witnesses", "crew",
                           "passengers", "police", "gendarmerie", "military witnesses"],
    "government_acknowledgment": ["government", "official", "air force acknowledged",
                                  "press conference", "declassified", "freedom of information"],
    "physical_sample": ["sample", "metal fragment", "material recovered", "soil sample",
                        "trace material", "debris"],
}


def keyword_score(text: str, keyword_dict: dict) -> tuple[list[str], float]:
    """Return (matched_tags, weighted_score) for a text against a keyword dict."""
    text_lower = text.lower()
    matched = []
    score = 0.0
    for tag, keywords in keyword_dict.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                matched.append(tag)
                score += 2.0 if tag in ("physical_evidence", "radar_confirmation", "EM_interference") else 1.0
                break
    return matched, score


def tag_feature(feature: dict) -> dict:
    """Enrich a GeoJSON feature with keyword-derived tags and confound flags."""
    props = feature.get("properties", {})
    text = " ".join(filter(None, [
        str(props.get("notes", "")),
        str(props.get("source", "")),
        str(props.get("layer", "")),
    ]))

    physical_tags, phys_score = keyword_score(text, PHYSICAL_EFFECT_KEYWORDS)
    confound_tags, _ = keyword_score(text, CONFOUND_KEYWORDS)
    secondary_tags, _ = keyword_score(text, SECONDARY_EFFECT_TAGS)

    # Cap physical effect score at 10
    physical_effect_score = min(round(phys_score, 1), 10.0)

    props["secondary_effect_tags"] = sorted(set(secondary_tags))
    props["physical_effect_score"] = physical_effect_score
    props["confound_flags"] = sorted(set(confound_tags))
    props["_tagged"] = True

    feature["properties"] = props
    return feature


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Haversine distance in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def parse_year(dt_str: str) -> int | None:
    """Extract year from ISO datetime string."""
    if not dt_str:
        return None
    try:
        return int(str(dt_str)[:4])
    except (ValueError, TypeError):
        return None


def dedup_features(features: list[dict], radius_km: float = 5.0, year_window: int = 1) -> list[dict]:
    """
    Assign incident_group_id and report_count to co-located features.
    Features are grouped if they are within radius_km and within year_window years.
    All records are kept; groups are linked by incident_group_id.
    """
    groups = []  # list of (group_id, lat, lon, year, [feature_indices])

    for i, feat in enumerate(features):
        geom = feat.get("geometry", {})
        if geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        year = parse_year(feat.get("properties", {}).get("datetime"))

        placed = False
        for group in groups:
            g_lat, g_lon, g_year = group["lat"], group["lon"], group["year"]
            dist = haversine_km(lat, lon, g_lat, g_lon)
            yr_diff = abs((year or 0) - (g_year or 0)) if (year and g_year) else 999
            if dist <= radius_km and yr_diff <= year_window:
                group["indices"].append(i)
                placed = True
                break

        if not placed:
            groups.append({
                "id": str(uuid.uuid4())[:8],
                "lat": lat, "lon": lon, "year": year,
                "indices": [i],
            })

    # Assign group info back to features
    multi_groups = [g for g in groups if len(g["indices"]) > 1]
    log.info(f"  Dedup: {len(features)} features → {len(groups)} groups "
             f"({len(multi_groups)} with >1 report)")

    for group in multi_groups:
        group_id = f"INC-{group['id']}"
        for idx in group["indices"]:
            props = features[idx].get("properties", {})
            if "incident_group_id" not in props:
                props["incident_group_id"] = group_id
                props["report_count"] = len(group["indices"])
                props["dedupe_confidence"] = "medium"
            features[idx]["properties"] = props

    return features


def process_file(path: Path) -> int:
    """Tag and dedup a single processed GeoJSON file. Returns features modified."""
    try:
        with open(path) as f:
            gj = json.load(f)
    except Exception as e:
        log.warning(f"  Could not read {path.name}: {e}")
        return 0

    features = gj.get("features", [])
    if not features:
        return 0

    # Tag
    features = [tag_feature(f) for f in features]

    # Dedup only for high-N self-report layers
    layer_name = path.stem
    high_n_layers = {"nuforc", "bfro_sightings", "maritime_anomalies", "noaa_ume",
                     "faa_wildlife_strikes", "usgs_seismic"}
    if layer_name in high_n_layers and len(features) > 20:
        features = dedup_features(features, radius_km=5.0, year_window=1)

    gj["features"] = features
    with open(path, "w") as f:
        json.dump(gj, f, separators=(",", ":"))

    return len(features)


def main():
    log.info("Starting event tagging + deduplication pass")
    geojson_files = sorted(PROCESSED_DATA_DIR.glob("*.geojson"))
    if not geojson_files:
        log.warning(f"No GeoJSON files found in {PROCESSED_DATA_DIR}")
        return

    total_tagged = 0
    for path in geojson_files:
        n = process_file(path)
        if n:
            log.info(f"  [OK] {path.name}: {n} features tagged")
            total_tagged += n

    log.info(f"Tag pass complete: {total_tagged} features across {len(geojson_files)} files")


if __name__ == "__main__":
    main()

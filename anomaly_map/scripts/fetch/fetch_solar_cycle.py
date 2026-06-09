"""
Layer 52: Solar Cycle vs. UAP Timeline Correlation
Source: SILSO/WDC-SILSO Royal Observatory Belgium monthly sunspot data
        NOAA NGDC solar cycle archive
        NUFORC flap period annotations

This is a COMPUTED layer — generates solar cycle phase records
aligned to known UAP flap periods for temporal correlation analysis.
"""
import os, sys, json, csv, io, logging
from datetime import datetime, date
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from common import make_record, records_to_geojson, save_geojson, fetch_with_retry, get_logger, save_raw

logger = get_logger("fetch_solar_cycle")

LAYER = "solar_cycle_correlation"
OUT_PATH = os.path.join(os.path.dirname(__file__), "../../data/processed/solar_cycle_correlation.geojson")
RAW_PATH = os.path.join(os.path.dirname(__file__), "../../data/raw/solar_cycle_monthly.csv")
ANALYSIS_PATH = os.path.join(os.path.dirname(__file__), "../../output/analysis/solar_uap_correlation.json")

# SILSO monthly mean sunspot number (updated monthly)
SILSO_URL = "https://www.sidc.be/silso/DATA/SN_m_tot_V2.0.txt"

# Solar cycle peaks and troughs (Solar Cycles 17-25)
# Solar_min/Solar_max, approximate dates
SOLAR_CYCLES = [
    {"cycle": 17, "min_date": "1933-09", "max_date": "1937-04", "max_ssn": 199},
    {"cycle": 18, "min_date": "1944-02", "max_date": "1947-05", "max_ssn": 218},
    {"cycle": 19, "min_date": "1954-04", "max_date": "1958-03", "max_ssn": 285},  # Largest recorded cycle
    {"cycle": 20, "min_date": "1964-10", "max_date": "1968-11", "max_ssn": 157},
    {"cycle": 21, "min_date": "1976-03", "max_date": "1979-12", "max_ssn": 233},
    {"cycle": 22, "min_date": "1986-09", "max_date": "1989-11", "max_ssn": 213},
    {"cycle": 23, "min_date": "1996-05", "max_date": "2000-03", "max_ssn": 180},
    {"cycle": 24, "min_date": "2008-12", "max_date": "2014-04", "max_ssn": 116},  # Weakest in 100 years
    {"cycle": 25, "min_date": "2019-12", "max_date": "2024-10", "max_ssn": 215},
]

# Known UAP flap periods with their solar cycle context
# Cross-referenced against NUFORC density peaks and NICAP documentation
UAP_FLAP_PERIODS = [
    {
        "period": "1947 Post-Roswell Wave",
        "start": "1947-06", "end": "1947-12",
        "solar_cycle": 18, "phase": "ascending",
        "estimated_ssn": 120,
        "notes": "First 'flying saucer' wave; coincides with SC18 ascending phase",
        "lat": 39.5, "lon": -98.4,
    },
    {
        "period": "1952 Washington DC Radar Wave",
        "start": "1952-07", "end": "1952-08",
        "solar_cycle": 19, "phase": "ascending",
        "estimated_ssn": 150,
        "notes": "SC19 ascending; Blue Book peak year; Washington National radar",
        "lat": 38.9, "lon": -77.0,
    },
    {
        "period": "1957 Levelland/Sputnik Wave",
        "start": "1957-10", "end": "1957-12",
        "solar_cycle": 19, "phase": "peak",
        "estimated_ssn": 260,
        "notes": "Near SC19 maximum (largest cycle in record); Sputnik launch Oct 1957; "
                 "Levelland EM-effect wave; correlation with atmospheric nuclear tests",
        "lat": 33.6, "lon": -102.0,
    },
    {
        "period": "1965-1967 Major US Wave",
        "start": "1965-01", "end": "1967-12",
        "solar_cycle": 20, "phase": "ascending",
        "estimated_ssn": 95,
        "notes": "SC20 ascending; Betty/Barney Hill era; sustained multi-year wave",
        "lat": 39.5, "lon": -98.4,
    },
    {
        "period": "1973 Pascagoula Wave",
        "start": "1973-09", "end": "1973-11",
        "solar_cycle": 20, "phase": "descending_late",
        "estimated_ssn": 75,
        "notes": "SC20 late descending; Pascagoula abduction claim; Ohio Coyne helicopter case",
        "lat": 30.4, "lon": -88.6,
    },
    {
        "period": "1977 Operation Prato / UK Wave",
        "start": "1977-01", "end": "1977-12",
        "solar_cycle": 21, "phase": "ascending",
        "estimated_ssn": 100,
        "notes": "SC21 ascending; Brazilian military investigation; concurrent UK wave; "
                 "Frederick Valentich disappearance 1978",
        "lat": -0.9, "lon": -47.6,
    },
    {
        "period": "1989-1990 Belgian Triangle Wave",
        "start": "1989-11", "end": "1991-04",
        "solar_cycle": 22, "phase": "peak",
        "estimated_ssn": 185,
        "notes": "Near SC22 maximum; Belgian Triangle wave + simultaneous Soviet wave; "
                 "F-16 radar 10,000g; independent international confirmation. "
                 "STRONGEST solar correlation: major wave at solar maximum.",
        "lat": 50.6, "lon": 5.5,
    },
    {
        "period": "2004 Nimitz Encounter",
        "start": "2004-11", "end": "2004-11",
        "solar_cycle": 23, "phase": "descending",
        "estimated_ssn": 60,
        "notes": "SC23 descending; Nimitz carrier group; Tic-Tac; radar confirmation; "
                 "ATFLIR video released 2017",
        "lat": 32.4, "lon": -119.4,
    },
    {
        "period": "2014-2015 Roosevelt Group Encounters",
        "start": "2014-06", "end": "2015-12",
        "solar_cycle": 24, "phase": "descending",
        "estimated_ssn": 110,
        "notes": "SC24 post-maximum; Roosevelt carrier group; Gimbal + GoFast videos; "
                 "weakest cycle in modern record — correlation INVERTED vs Belgian wave",
        "lat": 32.4, "lon": -75.0,
    },
    {
        "period": "2019 USS Russell Drone Swarm",
        "start": "2019-07", "end": "2019-07",
        "solar_cycle": 25, "phase": "minimum",
        "estimated_ssn": 8,
        "notes": "SC24/25 minimum — solar minimum, not maximum; drone swarm event; "
                 "near-zero sunspot number. Counters solar-maximum hypothesis.",
        "lat": 32.4, "lon": -119.4,
    },
    {
        "period": "2021-2024 AARO Reporting Surge",
        "start": "2021-01", "end": "2024-12",
        "solar_cycle": 25, "phase": "ascending_to_peak",
        "estimated_ssn": 150,
        "notes": "SC25 ascending to predicted strong maximum; AARO established 2022; "
                 "congressional hearings; Grusch testimony 2023; reporting bias confound high",
        "lat": 39.5, "lon": -98.4,
    },
]

# Key solar events that coincide with UAP flap periods
NOTABLE_SOLAR_EVENTS = [
    ("1957-09-04", 33.6, -102.0, "X-class solar flare", "SC19 peak; 2 months before Levelland wave"),
    ("1989-03-06", 50.6, 5.5, "X15 flare + Quebec blackout", "SC22 ascending; precedes Belgian wave peak"),
    ("1989-10-19", 50.6, 5.5, "Multiple X-class flares", "During Belgian Triangle wave; geomagnetic disturbance"),
    ("2003-10-28", 38.9, -77.0, "Halloween storm X17.2", "SC23 declining; largest modern storm"),
    ("2024-05-10", 38.9, -77.0, "G5 Carrington-class storm", "SC25 ascending; strongest storm since 2003"),
]


def fetch_silso_data():
    """Fetch SILSO monthly sunspot number time series."""
    try:
        logger.info("Fetching SILSO monthly sunspot data...")
        resp = fetch_with_retry(SILSO_URL, timeout=20)
        if not resp:
            return []

        lines = resp.text.strip().split("\n")
        save_raw(resp.content, RAW_PATH)

        monthly = []
        for line in lines:
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                year = int(parts[0])
                month = int(parts[1])
                ssn = float(parts[3])
                monthly.append({"year": year, "month": month, "ssn": ssn})
            except (ValueError, IndexError):
                continue

        logger.info(f"SILSO: {len(monthly)} monthly records ({monthly[0]['year'] if monthly else '?'} "
                    f"to {monthly[-1]['year'] if monthly else '?'})")
        return monthly
    except Exception as e:
        logger.warning(f"SILSO fetch failed: {e}")
        return []


def classify_solar_phase(ssn, cycle_max):
    """Classify solar phase based on sunspot number."""
    ratio = ssn / max(cycle_max, 1)
    if ratio < 0.15:
        return "solar_minimum"
    elif ratio < 0.40:
        return "early_ascending" if ssn > 0 else "solar_minimum"
    elif ratio < 0.70:
        return "ascending"
    elif ratio < 0.90:
        return "near_maximum"
    else:
        return "solar_maximum"


def build_solar_cycle_records(monthly_data):
    """Create spatial records at US centroid for solar cycle phase, for timeline correlation."""
    records = []
    cycle_lookup = {
        c["cycle"]: c for c in SOLAR_CYCLES
    }

    for entry in monthly_data:
        year, month, ssn = entry["year"], entry["month"], entry["ssn"]
        if year < 1947 or year > 2025:
            continue

        # Find which solar cycle this falls in
        sc_num = None
        for sc in SOLAR_CYCLES:
            min_y, min_m = [int(x) for x in sc["min_date"].split("-")]
            try:
                max_y, max_m = [int(x) for x in sc["max_date"].split("-")]
            except Exception:
                continue
            # Assign to cycle if between this minimum and next
            if (year * 12 + month) >= (min_y * 12 + min_m):
                sc_num = sc["cycle"]

        max_ssn = cycle_lookup.get(sc_num, {}).get("max_ssn", 200) if sc_num else 200
        phase = classify_solar_phase(ssn, max_ssn)

        dt = f"{year:04d}-{month:02d}-01"
        rec = make_record(
            layer=LAYER,
            lat=39.5,    # US centroid — this is a temporal/computed layer
            lon=-98.4,
            datetime=dt,
            confidence=0.95,
            category="geophysical",
            source="SILSO WDC Royal Observatory Belgium",
            notes=f"SC{sc_num or '?'} month {year}-{month:02d}: SSN={ssn:.1f} ({phase})"
        )
        rec["properties"]["sunspot_number"] = ssn
        rec["properties"]["solar_cycle"] = sc_num
        rec["properties"]["solar_phase"] = phase
        rec["properties"]["solar_cycle_max"] = max_ssn
        records.append(rec)

    return records


def build_flap_period_records():
    """Create records for each documented UAP flap period with solar context."""
    records = []
    for flap in UAP_FLAP_PERIODS:
        rec = make_record(
            layer=LAYER,
            lat=flap["lat"],
            lon=flap["lon"],
            datetime=flap["start"] + "-01",
            confidence=0.90,
            category="computed",
            source="NICAP / NUFORC flap documentation + SILSO solar data",
            notes=flap["notes"]
        )
        rec["properties"]["flap_period"] = flap["period"]
        rec["properties"]["solar_cycle"] = flap["solar_cycle"]
        rec["properties"]["solar_phase_at_flap"] = flap["phase"]
        rec["properties"]["estimated_ssn"] = flap["estimated_ssn"]
        rec["properties"]["flap_start"] = flap["start"]
        rec["properties"]["flap_end"] = flap["end"]
        records.append(rec)
    return records


def build_solar_event_records():
    records = []
    for date_str, lat, lon, event_name, notes in NOTABLE_SOLAR_EVENTS:
        rec = make_record(
            layer=LAYER,
            lat=lat,
            lon=lon,
            datetime=date_str,
            confidence=0.95,
            category="space_weather",
            source="NOAA NGDC Solar Event Catalog",
            notes=f"{event_name}: {notes}"
        )
        rec["properties"]["solar_event"] = event_name
        records.append(rec)
    return records


def compute_correlation(monthly_data, flap_periods):
    """Simple correlation: count how many flap months fall in high-SSN periods."""
    if not monthly_data:
        return {}

    ssn_by_ym = {(e["year"], e["month"]): e["ssn"] for e in monthly_data}
    flap_ssns = []
    non_flap_ssns = [e["ssn"] for e in monthly_data if 1947 <= e["year"] <= 2024]

    for flap in flap_periods:
        start_y, start_m = [int(x) for x in flap["start"].split("-")]
        end_y, end_m = [int(x) for x in flap["end"].split("-")]

        for (y, m), ssn in ssn_by_ym.items():
            ym = y * 12 + m
            if (start_y * 12 + start_m) <= ym <= (end_y * 12 + end_m):
                flap_ssns.append(ssn)

    if not flap_ssns or not non_flap_ssns:
        return {}

    mean_flap = sum(flap_ssns) / len(flap_ssns)
    mean_all = sum(non_flap_ssns) / len(non_flap_ssns)

    correlation = {
        "mean_ssn_during_flaps": round(mean_flap, 1),
        "mean_ssn_all_1947_2024": round(mean_all, 1),
        "ratio": round(mean_flap / max(mean_all, 1), 3),
        "flap_sample_months": len(flap_ssns),
        "total_months_analyzed": len(non_flap_ssns),
        "interpretation": (
            "Flaps slightly elevated vs. baseline (weak positive correlation)"
            if mean_flap > mean_all * 1.1 else
            "Flaps near baseline SSN (no strong solar correlation)"
            if abs(mean_flap - mean_all) < mean_all * 0.1 else
            "Flaps below baseline SSN (negative correlation — activity during solar minimum)"
        )
    }
    return correlation


def main():
    logger.info("=== Layer 52: Solar Cycle vs. UAP Timeline Correlation ===")

    monthly_data = fetch_silso_data()
    records = []

    if monthly_data:
        timeline_records = build_solar_cycle_records(monthly_data)
        records.extend(timeline_records)
        logger.info(f"Added {len(timeline_records)} monthly solar cycle records")

        correlation = compute_correlation(monthly_data, UAP_FLAP_PERIODS)
        os.makedirs(os.path.dirname(ANALYSIS_PATH), exist_ok=True)
        with open(ANALYSIS_PATH, "w") as f:
            json.dump({
                "solar_uap_correlation": correlation,
                "solar_cycles": SOLAR_CYCLES,
                "flap_periods": UAP_FLAP_PERIODS,
            }, f, indent=2)
        logger.info(f"Correlation analysis → {ANALYSIS_PATH}")
        logger.info(f"Correlation result: {correlation.get('interpretation', 'unknown')}")

    flap_records = build_flap_period_records()
    records.extend(flap_records)
    logger.info(f"Added {len(flap_records)} flap period annotation records")

    solar_event_records = build_solar_event_records()
    records.extend(solar_event_records)
    logger.info(f"Added {len(solar_event_records)} notable solar event records")

    gj = records_to_geojson(records, layer_id=LAYER, tier=2)
    save_geojson(gj, OUT_PATH)
    logger.info(f"Saved {len(records)} total records → {OUT_PATH}")


if __name__ == "__main__":
    main()

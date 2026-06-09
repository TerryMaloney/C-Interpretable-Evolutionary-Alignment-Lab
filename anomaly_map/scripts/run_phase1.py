"""
Phase 1 pipeline orchestrator — 25 layers + 2 masking layers.

Runs the full data acquisition + correlation analysis pipeline in sequence.
Can run all steps, sprint groups, or individual steps via CLI flags.

Usage:
  python scripts/run_phase1.py                       # Run full pipeline
  python scripts/run_phase1.py --sprint 1            # Sprint 1: geophysical baselines
  python scripts/run_phase1.py --sprint 2            # Sprint 2: high-N anomaly reports
  python scripts/run_phase1.py --sprint 3            # Sprint 3: physics-based detection
  python scripts/run_phase1.py --sprint 4            # Sprint 4: institutional data
  python scripts/run_phase1.py --sprint 5            # Sprint 5: manual geocoding
  python scripts/run_phase1.py --sprint 6            # Sprint 6: advanced raster analysis
  python scripts/run_phase1.py --masks               # Masking layers only
  python scripts/run_phase1.py --fetch               # All fetch steps
  python scripts/run_phase1.py --process             # normalize + merge
  python scripts/run_phase1.py --analyze             # clustering + correlation
  python scripts/run_phase1.py --viz                 # visualization
  python scripts/run_phase1.py --skip fetch_nuforc   # Skip specific step
"""

import argparse
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scripts.common import get_logger

log = get_logger("run_phase1")

# Sprint groupings from Layer Addendum
SPRINTS = {
    1: {
        "description": "Core geophysical baselines (Layers 4, 5, 6)",
        "steps": ["fetch_usgs_seismic", "fetch_usgs_magnetic", "fetch_usgs_radon"],
    },
    2: {
        "description": "High-N anomaly reports (Layers 1, 2, 18)",
        "steps": ["fetch_nuforc", "fetch_noaa_ume", "fetch_firms"],
    },
    3: {
        "description": "Physics-based detection: can't hide (Layers 19, 20, 21)",
        "steps": ["fetch_dart_buoys", "fetch_gps_tec", "fetch_sentinel5p"],
    },
    4: {
        "description": "Institutional data (Layers 3, 7, 8)",
        "steps": ["fetch_doe_grid", "fetch_epa_radnet", "fetch_nuclear_facilities"],
    },
    5: {
        "description": "Manual geocoding: context layers (Layers 9-15)",
        "steps": ["geocode_manual"],
    },
    6: {
        "description": "Advanced raster analysis (Layers 22, 24, 25)",
        "steps": ["fetch_ctbto_infrasound", "fetch_vlf_elf", "fetch_goes_ir"],
    },
    7: {
        "description": "Extended datasets: biological + FOIA + maritime + EM (Layers 26-35)",
        "steps": [
            "fetch_movebank",       # Layer 26: animal migration anomalies
            "fetch_bfro",           # Layer 27: BFRO sighting database
            "fetch_usgs_mines",     # Layer 28: MRDS mine locations
            "fetch_faa_wildlife",   # Layer 29: FAA wildlife strike database
            "fetch_water_wells",    # Layer 30: USGS NWIS groundwater wells
            "fetch_adsb",           # Layer 31: ADS-B traffic (noise control)
            "fetch_space_weather",  # Layer 32: NOAA space weather (solar control)
            "fetch_foia_docs",      # Layer 33: FOIA-derived institutional records
            "fetch_maritime",       # Layer 34: maritime anomaly incidents
            "fetch_schumann",       # Layer 35: Schumann resonance / ELF monitoring
        ],
    },
}

MASK_STEPS = ["fetch_faa_airspace", "fetch_nighttime_lights"]


def run_step(name: str, fn, skip_list: list[str]) -> bool:
    if name in skip_list:
        log.info(f"[SKIP] {name}")
        return True
    log.info(f"\n{'='*60}")
    log.info(f"STEP: {name}")
    log.info(f"{'='*60}")
    t0 = time.time()
    try:
        fn()
        elapsed = time.time() - t0
        log.info(f"[OK] {name} completed in {elapsed:.1f}s")
        return True
    except Exception as exc:
        log.error(f"[FAIL] {name}: {exc}")
        log.debug(traceback.format_exc())
        return False


def get_fetch_module(step_name: str):
    """Dynamically import a fetch module by step name."""
    module_name = step_name  # e.g. "fetch_nuforc"
    try:
        import importlib
        mod = importlib.import_module(f"scripts.fetch.{module_name}")
        return mod
    except ImportError as exc:
        log.error(f"Cannot import scripts.fetch.{module_name}: {exc}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Anomaly Map Phase 1 Pipeline")
    parser.add_argument("--sprint", type=int, choices=[1, 2, 3, 4, 5, 6, 7],
                        help="Run a specific sprint group only")
    parser.add_argument("--masks", action="store_true", help="Run masking layers only")
    parser.add_argument("--fetch", action="store_true", help="Run all fetch steps")
    parser.add_argument("--process", action="store_true", help="Run process/normalize steps")
    parser.add_argument("--analyze", action="store_true", help="Run analysis steps")
    parser.add_argument("--viz", action="store_true", help="Run visualization")
    parser.add_argument("--skip", nargs="+", default=[], help="Step names to skip")
    parser.add_argument("--list", action="store_true", help="List all steps and exit")
    args = parser.parse_args()

    if args.list:
        log.info("All pipeline steps:")
        for sprint_num, sprint in SPRINTS.items():
            log.info(f"\n  Sprint {sprint_num}: {sprint['description']}")
            for step in sprint["steps"]:
                log.info(f"    {step}")
        log.info(f"\n  Masks: {', '.join(MASK_STEPS)}")
        log.info("\n  Process: geocode_manual, normalize_all, merge_layers")
        log.info("  Analyze: population_control, clustering, correlation")
        log.info("  Viz: generate_map")
        return

    run_all = not any([args.sprint, args.masks, args.fetch, args.process, args.analyze, args.viz])
    results = {}

    # Determine which fetch steps to run
    fetch_steps_to_run = []

    if run_all or args.fetch:
        for sprint in SPRINTS.values():
            fetch_steps_to_run.extend(sprint["steps"])
        fetch_steps_to_run.extend(MASK_STEPS)
        fetch_steps_to_run = [s for s in fetch_steps_to_run if not s.startswith("geocode")]

    elif args.sprint:
        sprint_data = SPRINTS[args.sprint]
        log.info(f"\nRunning Sprint {args.sprint}: {sprint_data['description']}")
        fetch_steps_to_run = [s for s in sprint_data["steps"] if not s.startswith("geocode")]

    elif args.masks:
        fetch_steps_to_run = MASK_STEPS

    # Run fetch steps
    if fetch_steps_to_run:
        seen = set()
        for step_name in fetch_steps_to_run:
            if step_name in seen:
                continue
            seen.add(step_name)
            mod = get_fetch_module(step_name)
            if mod and hasattr(mod, "main"):
                results[step_name] = run_step(step_name, mod.main, args.skip)

    # Process steps (sprint 5 = geocode_manual; otherwise run when --process or full pipeline)
    if run_all or args.process or (args.sprint == 5):
        from scripts.process import geocode_manual
        from scripts.process import normalize_all
        from scripts.process import merge_layers

        process_steps = [
            ("geocode_manual", geocode_manual.main),
            ("normalize_all", normalize_all.main),
            ("merge_layers", merge_layers.main),
        ]
        for name, fn in process_steps:
            results[name] = run_step(name, fn, args.skip)

    # Analysis steps
    if run_all or args.analyze:
        from scripts.analyze import population_control
        from scripts.analyze import clustering
        from scripts.analyze import correlation

        analysis_steps = [
            ("population_control", population_control.main),
            ("clustering", clustering.main),
            ("correlation", correlation.main),
        ]
        for name, fn in analysis_steps:
            results[name] = run_step(name, fn, args.skip)

    # Visualization
    if run_all or args.viz:
        from scripts.viz import generate_map
        results["generate_map"] = run_step("generate_map", generate_map.main, args.skip)

    # Summary
    if results:
        log.info(f"\n{'='*60}")
        log.info("PIPELINE SUMMARY")
        log.info(f"{'='*60}")
        passed = sum(1 for v in results.values() if v)
        failed_steps = [k for k, v in results.items() if not v]
        for step, ok in results.items():
            status = "[OK]  " if ok else "[FAIL]"
            log.info(f"  {status} {step}")
        log.info(f"\n{passed} passed, {len(failed_steps)} failed")
        if failed_steps:
            log.info(f"\nFailed: {', '.join(failed_steps)}")
            log.info("Failures are often: missing API keys, network access, or optional deps.")
            log.info("Check logs above. Most failures are non-blocking for the analysis.")
        log.info("\nNext: open output/anomaly_map.html to inspect results.")
        log.info("Then review output/analysis/cluster_summary.json for signal strength.")
    else:
        log.info("No steps run. Use --list to see available steps.")


if __name__ == "__main__":
    main()

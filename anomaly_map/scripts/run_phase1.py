"""
Phase 1 pipeline orchestrator.

Runs the full data acquisition + correlation analysis pipeline in sequence.
Can run all steps or individual steps via CLI flags.

Usage:
  python scripts/run_phase1.py                    # Run full pipeline
  python scripts/run_phase1.py --fetch            # Only fetch step
  python scripts/run_phase1.py --process          # Only process/normalize
  python scripts/run_phase1.py --analyze          # Only analysis
  python scripts/run_phase1.py --viz              # Only visualization
  python scripts/run_phase1.py --skip nuforc      # Skip specific fetch script
"""

import argparse
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scripts.common import get_logger

log = get_logger("run_phase1")


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


def main():
    parser = argparse.ArgumentParser(description="Anomaly Map Phase 1 Pipeline")
    parser.add_argument("--fetch", action="store_true", help="Run fetch steps only")
    parser.add_argument("--process", action="store_true", help="Run process steps only")
    parser.add_argument("--analyze", action="store_true", help="Run analysis steps only")
    parser.add_argument("--viz", action="store_true", help="Run visualization only")
    parser.add_argument("--skip", nargs="+", default=[], help="Step names to skip")
    args = parser.parse_args()

    run_all = not any([args.fetch, args.process, args.analyze, args.viz])

    results = {}

    if run_all or args.fetch:
        from scripts.fetch import fetch_nuforc
        from scripts.fetch import fetch_usgs_seismic
        from scripts.fetch import fetch_usgs_magnetic
        from scripts.fetch import fetch_noaa_ume
        from scripts.fetch import fetch_doe_grid
        from scripts.fetch import fetch_usgs_radon
        from scripts.fetch import fetch_epa_radnet
        from scripts.fetch import fetch_nuclear_facilities

        fetch_steps = [
            ("fetch_nuforc", fetch_nuforc.main),
            ("fetch_usgs_seismic", fetch_usgs_seismic.main),
            ("fetch_usgs_magnetic", fetch_usgs_magnetic.main),
            ("fetch_noaa_ume", fetch_noaa_ume.main),
            ("fetch_doe_grid", fetch_doe_grid.main),
            ("fetch_usgs_radon", fetch_usgs_radon.main),
            ("fetch_epa_radnet", fetch_epa_radnet.main),
            ("fetch_nuclear_facilities", fetch_nuclear_facilities.main),
        ]

        for name, fn in fetch_steps:
            results[name] = run_step(name, fn, args.skip)

    if run_all or args.process:
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

    if run_all or args.viz:
        from scripts.viz import generate_map

        viz_steps = [("generate_map", generate_map.main)]
        for name, fn in viz_steps:
            results[name] = run_step(name, fn, args.skip)

    # Summary
    log.info(f"\n{'='*60}")
    log.info("PIPELINE SUMMARY")
    log.info(f"{'='*60}")
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    for step, ok in results.items():
        status = "[OK]  " if ok else "[FAIL]"
        log.info(f"  {status} {step}")
    log.info(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        log.info("\nFailed steps are often due to network access or missing deps.")
        log.info("Check individual script logs above for details.")
    log.info("\nNext: open output/anomaly_map.html in a browser to inspect results.")
    log.info("Then run analyze/clustering.py output to evaluate signal strength.")


if __name__ == "__main__":
    main()

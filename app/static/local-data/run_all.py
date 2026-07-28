#!/usr/bin/env python3
"""Run all scrapers sequentially. Tokens step skipped if tokens.json exists."""

import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPE_DIR = os.path.join(SCRIPT_DIR, "scripts")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

STEPS = [
    ("step1_get_tokens.py", "Tokens (Playwright)", True),
    ("step2_scrape_all_modules.py", "Modules (RP API)", False),
    ("step3_scrape_diplomas.py", "Diplomas (crawl4ai)", False),
    ("step4_scrape_minors.py", "Minors (crawl4ai)", False),
    ("step5_generate_career_paths.py", "Career Paths (generate)", False),
]


def run():
    print("=" * 50)
    print("  ModuleGo Scraper")
    print("=" * 50)

    t0 = time.time()
    total = len(STEPS)

    for i, (filename, label, skip_if_exists) in enumerate(STEPS, 1):
        path = os.path.join(SCRAPE_DIR, filename)
        if not os.path.exists(path):
            print(f"\n[{i}/{total}] [SKIP] {label}: {filename} not found")
            continue

        if skip_if_exists and os.path.exists(os.path.join(DATA_DIR, "tokens.json")):
            print(f"\n[{i}/{total}] [SKIP] {label}: tokens.json exists")
            continue

        print(f"\n[{i}/{total}] {label}...")
        step_t = time.time()
        result = subprocess.run([sys.executable, filename], cwd=SCRAPE_DIR, check=False)
        step_elapsed = time.time() - step_t
        if result.returncode != 0:
            print(f"\n[{i}/{total}] [FAIL] {label} (exit {result.returncode})")
            if skip_if_exists:
                print("  pip install -r requirements.txt && python -m playwright install chromium")
            sys.exit(result.returncode)
        print(f"[{i}/{total}] {label} done in {step_elapsed:.1f}s")

    elapsed = time.time() - t0
    print(f"\n{'=' * 50}")
    print(f"  Done in {elapsed:.1f}s")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run()

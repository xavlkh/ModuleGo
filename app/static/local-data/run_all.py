#!/usr/bin/env python3
"""
One-click: run all scrapers sequentially.
  step1  Get CSRF + moduleVersion tokens (agent-browser) — skipped if tokens.json exists
  step2  Scrape 537 modules synopsis
  step3  Generate comparison JSON
  step4  Scrape diplomas/curriculum
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPE_DIR = os.path.join(SCRIPT_DIR, "scripts")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

STEPS = [
    ("step1_get_tokens.py",        SCRAPE_DIR, "Get tokens (agent-browser)", True),   # skip_if_exists
    ("step2_scrape_all_modules.py", SCRAPE_DIR, "Scrape 537 modules synopsis", False),
    ("step3_generate_comparison.py", SCRAPE_DIR, "Generate modules comparison", False),
    ("step4_scrape_diplomas.py",    SCRAPE_DIR, "Scrape diplomas curriculum", False),
]

def run():
    for filename, workdir, label, skip_if_exists in STEPS:
        path = os.path.join(workdir, filename)
        if not os.path.exists(path):
            print(f"[SKIP] {label}: {path} not found")
            continue

        if skip_if_exists and os.path.exists(os.path.join(DATA_DIR, "tokens.json")):
            print(f"[SKIP] {label}: tokens.json already exists")
            continue

        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")
        result = subprocess.run(
            [sys.executable, filename],
            cwd=workdir,
        )
        if result.returncode != 0:
            if skip_if_exists:
                print(f"\n[FAIL] {label} failed. Install agent-browser or create tokens.json manually.")
                print("  npm install -g agent-browser")
            else:
                print(f"\n[FAIL] {label} exited with code {result.returncode}")
            sys.exit(result.returncode)

    print(f"\n{'='*60}")
    print("  ALL DONE")
    print(f"{'='*60}")

if __name__ == "__main__":
    run()

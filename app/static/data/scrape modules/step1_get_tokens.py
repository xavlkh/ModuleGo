import subprocess
import json
import re
import os
import time
import sys
from urllib.parse import unquote

URL = "https://lcs.rp.edu.sg/RPModuleSynopsis/"


def run(cmd, label=""):
    prefix = f"  {label}... " if label else ""
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip()
        sys.exit(f"{prefix}Failed: {error}")
    return result.stdout.strip()


def get_csrf():
    run(f'npx.cmd agent-browser open "{URL}"', "Opening RP page")
    raw = run('npx.cmd agent-browser eval "document.cookie"', "Reading cookie")
    cookie_js = raw.strip('"')
    match = re.search(r"(?:crf%3[Dd]|crf=)([a-zA-Z0-9%+=\/]+?)(?:%3[bB]|$)", cookie_js)
    if not match:
        sys.exit("Could not find CSRF token in cookie")
    csrf_raw = match.group(1)
    csrf = unquote(csrf_raw)
    print(f"  [OK] CSRF token: {csrf}")
    return csrf, cookie_js


def get_module_version():
    run("npx.cmd agent-browser network requests --clear", "Clearing network log")
    run('npx.cmd agent-browser type "A"', 'Typing "A" into search')
    run('npx.cmd agent-browser click "button[data-button]"', "Clicking search")
    time.sleep(1.5)
    net_json = run('npx.cmd agent-browser network requests --filter "ScreenDataSet" --json', "Capturing API request")

    try:
        net_data = json.loads(net_json)
    except json.JSONDecodeError as e:
        sys.exit(f"Failed to parse network data: {e}")

    requests_list = (
        net_data.get("data", net_data).get("requests", [])
        if isinstance(net_data, dict) else net_data
    )

    for req in requests_list:
        post_data = req.get("postData", "") or req.get("request", {}).get("postData", "")
        if not post_data:
            continue
        try:
            body = json.loads(post_data) if isinstance(post_data, str) else post_data
            mv = body.get("versionInfo", {}).get("moduleVersion", "")
            if mv:
                print(f"  [OK] Module version: {mv}")
                return mv
        except json.JSONDecodeError:
            continue

    sys.exit("Could not extract moduleVersion from network request")


def main():
    print(f"\nExtracting tokens from {URL}")
    print("-" * 50)

    csrf, cookie_js = get_csrf()
    module_version = get_module_version()

    tokens = {
        "csrf": csrf,
        "moduleVersion": module_version,
        "cookie": cookie_js,
    }

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)

    print("-" * 50)
    print(f"[OK] Saved to {path}")


if __name__ == "__main__":
    main()

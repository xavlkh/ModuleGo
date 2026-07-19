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
    print(f"{prefix}", end="", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip()
        print(f"FAIL")
        sys.exit(f"  Failed: {error}")
    print("OK")
    return result.stdout.strip()


def close_browser():
    subprocess.run("npx.cmd agent-browser close", capture_output=True, text=True, shell=True)


def check_node_npm():
    for cmd, name in [("node --version", "Node.js"), ("npm --version", "npm")]:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            sys.exit(f"  {name} is not installed. Install it from https://nodejs.org")


def ensure_agent_browser():
    result = subprocess.run("npx.cmd agent-browser --version", capture_output=True, text=True, shell=True)
    if result.returncode == 0:
        return True
    print("  agent-browser not found.")
    if "--no-install" not in sys.argv:
        print("  Installing agent-browser...")
        subprocess.run("npm install -g agent-browser", shell=True, check=True)
        print("  [OK] agent-browser installed")
    else:
        sys.exit("Install manually: npm install -g agent-browser")


def get_csrf():
    run(f'npx.cmd agent-browser open "{URL}"', "Opening RP page")
    raw = run('npx.cmd agent-browser eval "document.cookie"', "Reading cookie")
    cookie_js = raw.strip('"')
    match = re.search(r"(?:crf%3[Dd]|crf=)([a-zA-Z0-9%+=\/]+?)(?:%3[bB]|$)", cookie_js)
    if not match:
        close_browser()
        sys.exit("  Could not find CSRF token in cookie")
    csrf_raw = match.group(1)
    csrf = unquote(csrf_raw)
    print(f"  [OK] CSRF token: {csrf}")
    return csrf, cookie_js


def get_module_version():
    run("npx.cmd agent-browser network requests --clear", "Clearing network log")
    run('npx.cmd agent-browser type "A"', 'Typing "A" into search')
    run('npx.cmd agent-browser click "button[data-button]"', "Clicking search")

    print("  Waiting for API request", end="", flush=True)
    net_json = None
    for attempt in range(10):
        time.sleep(0.5)
        print(".", end="", flush=True)
        net_json = run('npx.cmd agent-browser network requests --filter "ScreenDataSet" --json', "")
        if net_json and "requests" in net_json:
            print(" Done")
            break
    else:
        print(" TIMEOUT")
        close_browser()
        sys.exit("  Could not capture API request after 5s")

    try:
        net_data = json.loads(net_json)
    except json.JSONDecodeError as e:
        close_browser()
        sys.exit(f"  Failed to parse network data: {e}")

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

    close_browser()
    sys.exit("  Could not extract moduleVersion from network request")


def main():
    print(f"\nExtracting tokens from {URL}")
    print("-" * 50)

    check_node_npm()
    ensure_agent_browser()
    csrf, cookie_js = get_csrf()
    module_version = get_module_version()

    tokens = {
        "csrf": csrf,
        "moduleVersion": module_version,
        "cookie": cookie_js,
    }

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "tokens.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)

    close_browser()

    print("-" * 50)
    print(f"[OK] Saved to {path}")


if __name__ == "__main__":
    main()

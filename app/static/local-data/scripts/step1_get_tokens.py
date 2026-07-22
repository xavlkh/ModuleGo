"""Extract RP API session tokens with Playwright.

The scraper uses the installed Google Chrome when available. A Playwright-
managed Chromium installation is used as a fallback for CI and machines that
do not have Chrome.
"""

import json
import os
import re
import sys
import time
from urllib.parse import unquote

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


URL = "https://lcs.rp.edu.sg/RPModuleSynopsis/"
REQUEST_NAME = "ScreenDataSet"
SEARCH_INPUT = "#InputSearchModuleCode"
SEARCH_BUTTON = "button[data-button]"
TOKEN_TIMEOUT_SECONDS = 10


def environment_flag(name, default=False):
    """Return a boolean environment variable using common true values."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def launch_browser(playwright, headed):
    """Launch signed system Chrome, falling back to Playwright Chromium."""
    launch_options = {"headless": not headed}
    try:
        return playwright.chromium.launch(channel="chrome", **launch_options)
    except PlaywrightError:
        try:
            return playwright.chromium.launch(**launch_options)
        except PlaywrightError as chromium_error:
            raise RuntimeError(
                "Could not launch Chrome or Playwright Chromium. Install a "
                "browser with: python -m playwright install chromium"
            ) from chromium_error


def extract_csrf(cookie_text):
    """Extract the OutSystems CSRF value from document.cookie."""
    match = re.search(
        r"(?:crf%3[Dd]|crf=)([a-zA-Z0-9%+=/]+?)(?:%3[bB]|$)",
        cookie_text,
    )
    if not match:
        raise RuntimeError("Could not find the CSRF token in the RP cookie.")
    return unquote(match.group(1))


def extract_module_version(captured_requests):
    """Return moduleVersion from a captured RP ScreenDataSet request."""
    for post_data in captured_requests:
        if not post_data:
            continue
        try:
            body = json.loads(post_data)
        except json.JSONDecodeError:
            continue
        module_version = body.get("versionInfo", {}).get("moduleVersion", "")
        if module_version:
            return module_version
    return ""


def capture_tokens(headed=False):
    """Open the RP page and capture its CSRF and module-version tokens."""
    captured_requests = []

    with sync_playwright() as playwright:
        browser = launch_browser(playwright, headed)
        try:
            context = browser.new_context()
            page = context.new_page()

            def remember_request(request):
                if REQUEST_NAME in request.url:
                    captured_requests.append(request.post_data)

            page.on("request", remember_request)

            print(f"  Opening RP page ({'headed' if headed else 'headless'})... ", end="", flush=True)
            page.goto(URL, wait_until="networkidle", timeout=60_000)
            print("OK")

            cookie_text = page.evaluate("document.cookie")
            csrf = extract_csrf(cookie_text)
            print("  [OK] CSRF token captured")

            page.locator(SEARCH_INPUT).fill("A")
            page.locator(SEARCH_BUTTON).click()

            deadline = time.monotonic() + TOKEN_TIMEOUT_SECONDS
            module_version = ""
            print("  Waiting for RP API request", end="", flush=True)
            while time.monotonic() < deadline:
                module_version = extract_module_version(captured_requests)
                if module_version:
                    break
                page.wait_for_timeout(500)
                print(".", end="", flush=True)
            print()

            if not module_version:
                raise RuntimeError(
                    "Could not capture moduleVersion from the RP API request."
                )

            print("  [OK] Module version captured")
            return {
                "csrf": csrf,
                "moduleVersion": module_version,
                "cookie": cookie_text,
            }
        finally:
            browser.close()


def main():
    """Capture tokens and save them in the gitignored local data folder."""
    print(f"\nExtracting tokens from {URL}")
    print("-" * 50)

    headed = environment_flag(
        "PLAYWRIGHT_HEADED",
        default=environment_flag("AGENT_BROWSER_HEADED"),
    )

    try:
        tokens = capture_tokens(headed=headed)
    except (PlaywrightError, RuntimeError) as error:
        sys.exit(f"  Failed: {error}")

    data_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data")
    )
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "tokens.json")
    with open(path, "w", encoding="utf-8") as token_file:
        json.dump(tokens, token_file, indent=2)

    print("-" * 50)
    print(f"[OK] Saved to {path}")


if __name__ == "__main__":
    main()

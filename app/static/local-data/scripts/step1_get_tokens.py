"""Step 1: Extract RP API session tokens with Playwright."""

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
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def launch_browser(playwright, headed):
    launch_options = {"headless": not headed}
    try:
        return playwright.chromium.launch(channel="chrome", **launch_options)
    except PlaywrightError:
        try:
            return playwright.chromium.launch(**launch_options)
        except PlaywrightError as chromium_error:
            raise RuntimeError(
                "Could not launch Chrome or Playwright Chromium. "
                "Install with: python -m playwright install chromium"
            ) from chromium_error


def extract_csrf(cookie_text):
    match = re.search(
        r"(?:crf%3[Dd]|crf=)([a-zA-Z0-9%+=/]+?)(?:%3[bB]|$)",
        cookie_text,
    )
    if not match:
        raise RuntimeError("Could not find CSRF token in RP cookie.")
    return unquote(match.group(1))


def extract_module_version(captured_requests):
    for post_data in captured_requests:
        if not post_data:
            continue
        try:
            body = json.loads(post_data)
        except json.JSONDecodeError:
            continue
        mv = body.get("versionInfo", {}).get("moduleVersion", "")
        if mv:
            return mv
    return ""


def capture_tokens(headed=False):
    captured_requests = []

    with sync_playwright() as pw:
        browser = launch_browser(pw, headed)
        try:
            ctx = browser.new_context()
            page = ctx.new_page()

            def on_request(request):
                if REQUEST_NAME in request.url:
                    captured_requests.append(request.post_data)

            page.on("request", on_request)

            print(f"  Opening RP page ({'headed' if headed else 'headless'})...")
            page.goto(URL, wait_until="networkidle", timeout=60_000)

            csrf = extract_csrf(page.evaluate("document.cookie"))
            print("  CSRF captured")

            page.locator(SEARCH_INPUT).fill("A")
            page.locator(SEARCH_BUTTON).click()

            deadline = time.monotonic() + TOKEN_TIMEOUT_SECONDS
            mv = ""
            while time.monotonic() < deadline:
                mv = extract_module_version(captured_requests)
                if mv:
                    break
                page.wait_for_timeout(500)

            if not mv:
                raise RuntimeError("Could not capture moduleVersion.")

            print("  Module version captured")
            return {"csrf": csrf, "moduleVersion": mv, "cookie": page.evaluate("document.cookie")}
        finally:
            browser.close()


def main():
    print("\n[1/4] Tokens")
    print("-" * 50)

    headed = environment_flag("PLAYWRIGHT_HEADED", default=environment_flag("AGENT_BROWSER_HEADED"))

    try:
        tokens = capture_tokens(headed=headed)
    except (PlaywrightError, RuntimeError) as error:
        sys.exit(f"  FAILED: {error}")

    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "tokens.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)

    print(f"  Saved {path}")
    print("-" * 50)


if __name__ == "__main__":
    main()

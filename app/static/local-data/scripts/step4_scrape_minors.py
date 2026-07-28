"""Step 4: Scrape minor programmes via crawl4ai (concurrent)."""

import asyncio
import csv
import json
import os
import re
import time

import httpx
from bs4 import BeautifulSoup

MODULE_RE = re.compile(r"^\s*\*?\s*([A-Z]\d{3}[A-Z]?)\s+(.+)$")

LISTING_URL = "https://www.rp.edu.sg/designing-your-learning/minor-programmes/"


def fetch_minor_urls_and_types():
    """Fetch minor URLs from sitemap and types from the listing page."""
    # Get URLs from sitemap
    resp = httpx.get("https://www.rp.edu.sg/sitemap.xml", headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "xml")
    all_urls = [
        loc.text for loc in soup.find_all("loc")
        if "/minor-programmes/minor-in" in loc.text
    ]

    # Get type mapping from listing page
    page = httpx.get(LISTING_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    page.raise_for_status()
    psoup = BeautifulSoup(page.text, "html.parser")
    type_map = {}
    table = psoup.find("table")
    if table:
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        for th, td in zip(headers, table.find_all("td")):
            minor_type = "Broad-Based" if "Broad" in th else "Discipline-Related"
            for a in td.find_all("a", href=True):
                if "/minor-in" in a["href"]:
                    url = a["href"].rstrip("/") + "/"
                    if not url.startswith("http"):
                        url = "https://www.rp.edu.sg" + url
                    type_map[url] = minor_type

    return all_urls, type_map


def parse_modules(markdown):
    modules, in_section = [], False
    for line in markdown.split("\n"):
        s = line.strip()
        if s.startswith("## Modules"):
            in_section = True
            continue
        if in_section and s.startswith("## "):
            break
        if in_section:
            match = MODULE_RE.match(s)
            if match:
                modules.append({"code": match.group(1), "name": match.group(2).strip()})
    seen = set()
    return [m for m in modules if m["code"] not in seen and not seen.add(m["code"])]


def parse_eligibility(markdown):
    in_section, lines = False, []
    for line in markdown.split("\n"):
        s = line.strip()
        if "Who can apply" in s:
            in_section = True
            continue
        if in_section and s.startswith("## "):
            break
        if in_section and s:
            lines.append(s)
    return " ".join(lines).strip()


async def main():
    from crawl4ai import AsyncWebCrawler

    print("\n[4/4] Minors")
    print("-" * 50)

    urls, type_map = fetch_minor_urls_and_types()
    print(f"  Found {len(urls)} minor URLs from sitemap")
    print("  Crawling concurrently...")
    t0 = time.time()

    async with AsyncWebCrawler() as crawler:
        results_raw = await crawler.arun_many(urls, config=None)

    results = []
    # URL slugs drop special chars — fix known mismatches
    SLUG_NAME_FIXES = {
        "fb": "F&B",
    }

    for r in results_raw:
        minor_type = type_map.get(r.url, "Broad-Based")
        slug = r.url.rstrip("/").split("/")[-1]
        # slug = "minor-in-business" -> "Minor in Business"
        name = slug.replace("-", " ")
        words = name.split()
        minor_name = " ".join(
            SLUG_NAME_FIXES.get(w.lower(), w.upper() if len(w) <= 2 and w.isalpha() and w.upper() not in ("IN", "OF", "AND", "FOR", "THE") else w.title())
            for w in words
        )
        if not minor_name.lower().startswith("minor in"):
            minor_name = "Minor in " + minor_name.split("minor in", 1)[-1]
        # Force "Minor in" lowercase to match RP convention
        minor_name = re.sub(r"^Minor\s+In\b", "Minor in", minor_name)
        if not r.success:
            print(f"  FAILED: {minor_name}")
            results.append({"minor_type": minor_type, "minor_name": minor_name, "url": r.url, "modules": [], "eligibility": ""})
            continue
        modules = parse_modules(r.markdown)
        eligibility = parse_eligibility(r.markdown)
        results.append({"minor_type": minor_type, "minor_name": minor_name, "url": r.url, "modules": modules, "eligibility": eligibility})
        print(f"  {minor_name}: {len(modules)} modules")

    # Deduplicate by lowercased name (safety net)
    seen_names = set()
    deduped = []
    for r in results:
        key = r["minor_name"].lower()
        if key not in seen_names:
            seen_names.add(key)
            deduped.append(r)
    results = deduped

    results.sort(key=lambda x: x["minor_name"])
    elapsed = time.time() - t0
    print(f"  Scraped {len(results)} minors in {elapsed:.1f}s")

    # Save
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    json_path = os.path.join(data_dir, "rp_minors.json")
    csv_path = os.path.join(data_dir, "rp_minors.csv")

    def _write_files():
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["minor_type", "minor_name", "url", "modules", "eligibility"])
            writer.writeheader()
            for row in results:
                csv_row = dict(row)
                csv_row["modules"] = json.dumps([m["code"] for m in csv_row["modules"]])
                writer.writerow(csv_row)

    await asyncio.to_thread(_write_files)
    print(f"  Saved {json_path}")
    print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())

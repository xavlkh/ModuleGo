"""Step 3: Scrape diploma pages via crawl4ai (concurrent)."""

import asyncio
import csv
import json
import os
import re
import time

from bs4 import BeautifulSoup

SCHOOL_MAP = {
    "School of Applied Science": "SAS", "School of Business": "SBZ",
    "School of Engineering": "SEG", "School of Hospitality": "SOH",
    "School of Infocomm": "SOI", "School of Sports and Health": "SSH",
    "School of Technology for Arts, Media and Design": "STA",
    "General": "General", "CENTRE FOR FOUNDATIONAL STUDIES": "General",
}

MODULE_RE = re.compile(r'^([A-Z]\d{3}[A-Z]?)\s+(.+)$')


def extract_data(html):
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string if soup.title else ""
    course_code, course_name = "", ""
    if "(" in title and ")" in title:
        course_code = title.split("(")[-1].split(")")[0]
        course_name = title.split("(")[0].strip()

    school_name = ""
    for div in soup.find_all("div", class_="prose-body-base"):
        text = div.get_text(strip=True)
        if text.startswith(("School of", "CENTRE FOR")):
            school_name = text
            break
    if school_name == "School of Technology for the Arts":
        school_name = "School of Technology for Arts, Media and Design"
    school_abbr = SCHOOL_MAP.get(school_name, "")

    buckets = {"general": [], "major": [], "discipline": [], "elective": [], "industry": []}
    major_groups = {}  # {major_name: [module_codes]}

    for details in soup.find_all("details"):
        summary = details.find("summary")
        if not summary:
            continue
        st = summary.get_text(strip=True)

        if "General Modules" in st:
            current = "general"
        elif "Major Modules" in st:
            current = "major"
        elif "Discipline Modules" in st:
            current = "discipline"
        elif "Elective Modules" in st:
            current = "elective"
        elif "Industry Orientation Programme Modules" in st:
            current = "industry"
        else:
            continue

        # Extract all modules from this details section
        for a in details.find_all("a", href=True):
            if "/education/modules/" in a["href"]:
                code = a["href"].split("/modules/")[-1].strip("/").upper()
                name = a.get_text(strip=True)
                if name.upper().startswith(code):
                    name = name[len(code):].strip()
                buckets[current].append({"code": code, "name": name})

        for li in details.find_all("li"):
            if li.find("a", href=lambda h: h and "/education/modules/" in h):
                continue
            match = MODULE_RE.match(li.get_text(strip=True))
            if match:
                buckets[current].append({"code": match.group(1), "name": match.group(2).strip()})

        # For major sections, group modules by major sub-headings
        if current == "major":
            # Find the container div that holds the major groupings
            container = details
            inner_div = details.find("div")
            if inner_div:
                container = inner_div

            # Walk children of container to map headings to modules
            # Headings are <p> tags with text like "Major in Full Stack Development"
            active_major = None
            for child in container.children:
                if not hasattr(child, 'name') or child.name is None:
                    continue
                text = child.get_text(strip=True)
                # Detect major heading (<p>Major in X</p>, <b>Major in X</b>, <strong>Major in X</strong>)
                if text.lower().startswith("major in") and child.name in ("p", "b", "strong", "h3", "h4"):
                    active_major = text
                    major_groups[active_major] = []
                    continue
                # Collect modules under current major
                if active_major:
                    for a in child.find_all("a", href=True) if hasattr(child, 'find_all') else []:
                        if "/education/modules/" in a["href"]:
                            code = a["href"].split("/modules/")[-1].strip("/").upper()
                            if code not in major_groups[active_major]:
                                major_groups[active_major].append(code)
                    if hasattr(child, 'find_all'):
                        for li in child.find_all("li"):
                            m = MODULE_RE.match(li.get_text(strip=True))
                            if m and m.group(1) not in major_groups[active_major]:
                                major_groups[active_major].append(m.group(1))

    def dedup(lst):
        seen = set()
        return [item for item in lst if item["code"] not in seen and not seen.add(item["code"])]

    # Deduplicate major_groups values
    deduped_groups = {}
    for name, codes in major_groups.items():
        seen = set()
        deduped_groups[name] = [c for c in codes if c not in seen and not seen.add(c)]

    result = {
        "course_code": course_code, "course_name": course_name,
        "school_name": school_name, "school_abbr": school_abbr,
        **{f"{k}_modules": dedup(v) for k, v in buckets.items()},
    }
    if deduped_groups:
        result["major_groups"] = deduped_groups
    return result


async def main():
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError:
        print("ERROR: crawl4ai not installed. Run: pip install crawl4ai && crawl4ai-setup")
        return

    print("\n[3/5] Diplomas")
    print("-" * 50)

    # Fetch sitemap for diploma URLs
    import httpx
    from bs4 import BeautifulSoup as BS

    resp = await asyncio.to_thread(
        httpx.get, "https://www.rp.edu.sg/sitemap.xml",
        headers={"User-Agent": "Mozilla/5.0"}, timeout=30
    )
    soup = BS(resp.text, "xml")
    base = "https://www.rp.edu.sg"
    urls = [loc.text for loc in soup.find_all("loc") if "/education/diplomas/" in loc.text and loc.text.rstrip("/") != f"{base}/education/diplomas"]
    print(f"  Found {len(urls)} diploma URLs, crawling concurrently...")

    t0 = time.time()

    async with AsyncWebCrawler() as crawler:
        results_raw = await crawler.arun_many(urls, config=None)

    results = []
    for r in results_raw:
        if not r.success:
            print(f"  FAILED: {r.url}")
            continue
        data = extract_data(r.html)
        data["url"] = r.url
        if data["course_code"]:
            results.append(data)
            g = len(data["general_modules"])
            m = len(data["major_modules"])
            d = len(data["discipline_modules"])
            e = len(data["elective_modules"])
            i = len(data["industry_modules"])
            mg = data.get("major_groups", {})
            mg_info = f" [{len(mg)} majors]" if mg else ""
            print(f"  {data['course_code']}: {data['course_name'][:45]} | {g}g {m}m{mg_info} {d}d {e}e {i}i")

    results.sort(key=lambda d: d["course_code"])
    elapsed = time.time() - t0
    print(f"  Scraped {len(results)} diplomas in {elapsed:.1f}s")

    # Save
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    json_path = os.path.join(data_dir, "rp_courses.json")
    csv_path = os.path.join(data_dir, "rp_courses.csv")
    fields = ["course_code", "course_name", "school_name", "school_abbr", "url",
              "general_modules", "major_modules", "discipline_modules", "elective_modules", "industry_modules",
              "major_groups"]

    def _write_files():
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for d in results:
                row = {k: d[k] for k in fields[:5]}
                for key in fields[5:10]:
                    row[key] = json.dumps([m["code"] for m in d.get(key, [])])
                row["major_groups"] = json.dumps(d.get("major_groups", {}))
                w.writerow(row)

    await asyncio.to_thread(_write_files)

    print(f"  Saved {json_path}")
    print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())

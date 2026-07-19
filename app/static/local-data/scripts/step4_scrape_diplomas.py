import httpx
import json
import os
import csv
import time
from bs4 import BeautifulSoup

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")  # local-data/data/
BASE_URL = "https://www.rp.edu.sg"

SCHOOL_MAP = {
    "School of Applied Science": "SAS",
    "School of Business": "SBZ",
    "School of Engineering": "SEG",
    "School of Hospitality": "SOH",
    "School of Infocomm": "SOI",
    "School of Sports and Health": "SSH",
    "School of Technology for Arts, Media and Design": "STA",
    "School of Technology for the Arts": "STA",
}

def extract_data(html):
    """Extract course info and curriculum from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")

    # Course code and name from title
    title = soup.title.string if soup.title else ""
    course_code = ""
    course_name = ""
    if "(" in title and ")" in title:
        course_code = title.split("(")[-1].split(")")[0]
        course_name = title.split("(")[0].strip()

    # School name
    school_name = ""
    school_abbr = ""
    for div in soup.find_all("div", class_="prose-body-base"):
        text = div.get_text(strip=True)
        if text.startswith("School of"):
            school_name = text
            school_abbr = SCHOOL_MAP.get(text, "")
            break

    # Curriculum
    general, discipline, major, elective, industry = [], [], [], [], []
    for details in soup.find_all("details"):
        summary = details.find("summary")
        if not summary:
            continue
        summary_text = summary.get_text(strip=True)

        if "General Modules" in summary_text:
            current_type = "general"
        elif "Major Modules" in summary_text:
            current_type = "major"
        elif "Discipline Modules" in summary_text:
            current_type = "discipline"
        elif "Elective Modules" in summary_text:
            current_type = "elective"
        elif "Industry Orientation Programme Modules" in summary_text:
            current_type = "industry"
        else:
            continue

        for a in details.find_all("a", href=True):
            if "/education/modules/" in a["href"]:
                code = a["href"].split("/modules/")[-1].strip("/").upper()
                name = a.get_text(strip=True)
                # Strip redundant code prefix from name (e.g., "G121 Innovation and Practice" -> "Innovation and Practice")
                if name.upper().startswith(code):
                    name = name[len(code):].strip()
                entry = {"code": code, "name": name}
                if current_type == "general":
                    general.append(entry)
                elif current_type == "major":
                    major.append(entry)
                elif current_type == "discipline":
                    discipline.append(entry)
                elif current_type == "elective":
                    elective.append(entry)
                elif current_type == "industry":
                    industry.append(entry)

    def dedup(lst):
        seen = set()
        return [item for item in lst if item["code"] not in seen and not seen.add(item["code"])]

    return {
        "course_code": course_code,
        "course_name": course_name,
        "school_name": school_name,
        "school_abbr": school_abbr,
        "general_modules": dedup(general),
        "major_modules": dedup(major),
        "discipline_modules": dedup(discipline),
        "elective_modules": dedup(elective),
        "industry_modules": dedup(industry),
    }

# Fetch sitemap
print("Fetching sitemap...")
with httpx.Client() as client:
    sitemap = client.get(f"{BASE_URL}/sitemap.xml", follow_redirects=True, timeout=30).text
    soup = BeautifulSoup(sitemap, "xml")
    urls = [loc.text for loc in soup.find_all("loc") if "/education/diplomas/" in loc.text and loc.text.rstrip("/") != f"{BASE_URL}/education/diplomas"]
    print(f"Found {len(urls)} diploma URLs")

    results = []
    for i, url in enumerate(urls):
        slug = url.split("/diplomas/")[-1].rstrip("/")
        print(f"[{i+1}/{len(urls)}] {slug}")

        try:
            resp = client.get(url, follow_redirects=True, timeout=30)
            resp.raise_for_status()
            data = extract_data(resp.text)
            data["url"] = url
            results.append(data)
            g, m, d, e, i = len(data["general_modules"]), len(data["major_modules"]), len(data["discipline_modules"]), len(data["elective_modules"]), len(data["industry_modules"])
            print(f"  OK: {data['course_code']} - {data['course_name'][:40]} | {g} gen, {m} major, {d} disc, {e} elec, {i} ind")
        except Exception as exc:
            print(f"  ERROR: {exc}")

        time.sleep(1)

# Filter invalid entries and sort by course_code
results = [d for d in results if d.get("course_code")]
results.sort(key=lambda d: d["course_code"])

# Save JSON
os.makedirs(BASE_DIR, exist_ok=True)
json_path = os.path.join(BASE_DIR, "rp_diplomas_curriculum.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\nSaved {len(results)} diplomas to {json_path}")

# Save CSV
csv_rows = []
for d in results:
    csv_rows.append({
        "course_code": d["course_code"],
        "course_name": d["course_name"],
        "school_name": d["school_name"],
        "school_abbr": d["school_abbr"],
        "url": d["url"],
        "general_modules": json.dumps([m["code"] for m in d["general_modules"]]),
        "major_modules": json.dumps([m["code"] for m in d["major_modules"]]),
        "discipline_modules": json.dumps([m["code"] for m in d["discipline_modules"]]),
        "elective_modules": json.dumps([m["code"] for m in d["elective_modules"]]),
        "industry_modules": json.dumps([m["code"] for m in d["industry_modules"]]),
    })

fields = ["course_code", "course_name", "school_name", "school_abbr", "url", "general_modules", "major_modules", "discipline_modules", "elective_modules", "industry_modules"]
csv_path = os.path.join(BASE_DIR, "rp_diplomas_curriculum.csv")
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(csv_rows)
print(f"Saved {len(csv_rows)} rows to {csv_path}")

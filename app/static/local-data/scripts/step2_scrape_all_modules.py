"""Step 2: Scrape modules from RP API (A-Z prefix iteration)."""

import csv
import json
import os
import string
import time

import httpx

API_URL = "https://lcs.rp.edu.sg/RPModuleSynopsis/screenservices/RPModuleSynopsis/MainFlow/ModuleSynopsis/ScreenDataSetGetSynopsis?lXamMASFpg1bQfatzeulEg"

PREFIX_SCHOOL = {
    "A": "School of Applied Science", "B": "School of Business",
    "C": "School of Infocomm", "E": "School of Engineering",
    "G": "General", "H": "School of Hospitality",
    "M": "School of Business", "P": "General",
    "S": "School of Sports and Health",
    "T": "School of Technology for Arts, Media and Design",
}

SCHOOL_ABBR = {
    "School of Applied Science": "SAS", "School of Business": "SBZ",
    "School of Engineering": "SEG", "School of Hospitality": "SOH",
    "School of Infocomm": "SOI", "School of Sports and Health": "SSH",
    "School of Technology for Arts, Media and Design": "STA",
    "General": "General", "CENTRE FOR FOUNDATIONAL STUDIES": "General",
}

GENERAL_PREFIXES = {"G", "P"}


def fix_mojibake(text):
    if not isinstance(text, str):
        return text
    try:
        fixed = text.encode("latin-1").decode("utf-8")
        if fixed != text:
            text = fixed
    except (UnicodeDecodeError, UnicodeEncodeError, UnicodeTranslateError):
        pass
    return text.replace("\u000b", " ").replace("\u00a0", " ").replace("\u200b", "")


def should_keep(module, seen_codes):
    """Return True if this module entry should replace the existing one.

    Dedup rule: when the same code appears under multiple schools,
    keep the one whose school matches the prefix's owning school.
    If both match, keep the later one (last-wins).
    """
    code = module.get("module_code", "")
    school = module.get("school_name", "")
    if code not in seen_codes:
        return True
    expected = PREFIX_SCHOOL.get(code[0].upper(), "")
    if not expected:
        return False
    existing_school = seen_codes[code][0]
    # Keep if this entry's school matches expected AND existing doesn't
    return school == expected and existing_school != expected


def fetch(code, start, csrf, mv, cookie):
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json",
        "X-CSRFToken": csrf,
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    payload = {
        "versionInfo": {"moduleVersion": mv, "apiVersion": "lXamMASFpg1bQfatzeulEg"},
        "viewName": "MainFlow.ModuleSynopsis",
        "screenData": {"variables": {
            "searchModuleCode": code,
            "searchModuleDescription": "",
            "StartIndex": start,
            "MaxRecords": 500,
        }},
        "inputParameters": {"StartIndex": start, "MaxRecords": 500},
    }
    resp = httpx.post(API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_modules(data):
    modules = []
    list_wrapper = (data.get("data") or {}).get("List", {})
    rows = list_wrapper.get("List", []) if isinstance(list_wrapper, dict) else list_wrapper
    for row in rows:
        if not isinstance(row, dict):
            continue
        syn = row.get("Synopsis", {}) or {}
        dept = row.get("Departments", {}) or {}
        modules.append({
            "module_code": fix_mojibake(syn.get("Module_Code", "")),
            "module_name": fix_mojibake(syn.get("Module_Description", "")),
            "synopsis": fix_mojibake(syn.get("Synopsis", "")),
            "school_name": fix_mojibake(dept.get("Name", "")),
        })
    return modules


def get_school_abbr(school_name):
    name = (school_name or "").strip().upper()
    if name == "GENERAL" or "CENTRE FOR FOUNDATIONAL" in name or "FOUNDATIONAL STUDIES" in name:
        return "General"
    return SCHOOL_ABBR.get(school_name, "")


def main():
    print("\n[2/5] Modules")
    print("-" * 50)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    token_path = os.path.join(data_dir, "tokens.json")
    with open(token_path, "r", encoding="utf-8") as f:
        tokens = json.load(f)

    all_modules = []
    seen_codes = {}  # code -> (school_name, index_in_all_modules)
    t0 = time.time()

    for prefix in string.ascii_uppercase:
        start, page = 0, 1
        while True:
            try:
                data = fetch(prefix, start, tokens["csrf"], tokens["moduleVersion"], tokens["cookie"])
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    print(f"  {prefix}: tokens expired at offset {start}")
                    break
                raise
            count = (data.get("data") or {}).get("Count", 0) or 0
            for m in extract_modules(data):
                code = m["module_code"]
                if not code:
                    continue
                if should_keep(m, seen_codes):
                    if code in seen_codes:
                        _, idx = seen_codes[code]
                        all_modules[idx] = m
                    else:
                        seen_codes[code] = (m.get("school_name", ""), len(all_modules))
                        all_modules.append(m)
            if page == 1 and count > 0:
                print(f"  {prefix}: {count} modules")
            start += 500
            page += 1
            if start >= count:
                break

    elapsed = time.time() - t0
    print(f"  Fetched {len(all_modules)} unique modules in {elapsed:.1f}s")

    # Enrich with school_abbr, url
    output = []
    for m in all_modules:
        code = m["module_code"]
        prefix = code[0].upper() if code else "X"

        if prefix in GENERAL_PREFIXES:
            school_name, school_abbr = "General", "General"
        else:
            school_name = m.get("school_name", "") or PREFIX_SCHOOL.get(prefix, "")
            school_abbr = get_school_abbr(school_name)

        url = f"https://www.rp.edu.sg/education/modules/{code.lower()}"
        output.append({
            "module_code": code, "module_name": m["module_name"],
            "synopsis": m["synopsis"], "school_name": school_name,
            "school_abbr": school_abbr, "url": url,
        })

    output.sort(key=lambda m: m["module_code"])

    os.makedirs(data_dir, exist_ok=True)
    json_path = os.path.join(data_dir, "rp_modules_synopsis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    csv_path = os.path.join(data_dir, "rp_modules_synopsis.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["module_code", "module_name", "synopsis", "school_name", "school_abbr", "url"])
        writer.writeheader()
        writer.writerows(output)

    print(f"  Saved {json_path}")
    print("-" * 50)


if __name__ == "__main__":
    main()

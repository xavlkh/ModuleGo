import requests
import json
import csv
import time
import string
import os
import re

API_URL = "https://lcs.rp.edu.sg/RPModuleSynopsis/screenservices/RPModuleSynopsis/MainFlow/ModuleSynopsis/ScreenDataSetGetSynopsis?lXamMASFpg1bQfatzeulEg"

PREFIX_SCHOOL = {
    "A": "School of Applied Science",
    "B": "School of Business",
    "C": "School of Infocomm",
    "E": "School of Engineering",
    "G": "General",
    "H": "School of Hospitality",
    "M": "School of Business",
    "P": "General",
    "S": "School of Sports and Health",
    "T": "School of Technology for Arts, Media and Design",
}

SCHOOL_ABBR = {
    "School of Applied Science": "SAS",
    "School of Business": "SBZ",
    "School of Engineering": "SEG",
    "School of Hospitality": "SOH",
    "School of Infocomm": "SOI",
    "School of Sports and Health": "SSH",
    "School of Technology for Arts, Media and Design": "STA",
    "School of Technology for the Arts": "STA",
    "General": "General",
    "CENTRE FOR FOUNDATIONAL STUDIES": "General",
}


def fix_mojibake(text):
    if not isinstance(text, str):
        return text
    try:
        fixed = text.encode("latin-1").decode("utf-8")
        if fixed != text:
            text = fixed
    except (UnicodeDecodeError, UnicodeEncodeError, UnicodeTranslateError):
        pass
    text = text.replace("\u000b", " ")
    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    return text


def should_keep(module, seen_codes):
    code = module.get("module_code", "")
    school = module.get("school_name", "")
    if code not in seen_codes:
        return True
    expected = PREFIX_SCHOOL.get(code[0].upper(), "")
    if not expected:
        return False
    if school == expected and seen_codes[code] != expected:
        return True
    return False


def fetch(code="", start=0, max_rec=500, csrf="", mv="", cookie=""):
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
            "MaxRecords": max_rec,
        }},
        "inputParameters": {"StartIndex": start, "MaxRecords": max_rec},
    }
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_modules(data, prefix):
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(script_dir, "tokens.json")
    with open(token_path, "r", encoding="utf-8") as f:
        tokens = json.load(f)
    csrf = tokens.get("csrf", "")
    mv = tokens.get("moduleVersion", "")
    cookie = tokens.get("cookie", "")

    all_modules = []
    seen_codes = {}

    for prefix in string.ascii_uppercase:
        print(f"Fetching prefix {prefix}...")
        start = 0
        page = 1
        while True:
            try:
                data = fetch(code=prefix, start=start, max_rec=500, csrf=csrf, mv=mv, cookie=cookie)
            except requests.HTTPError as e:
                if e.response.status_code == 403:
                    print(f"  403 at {prefix} start={start} — tokens expired")
                    break
                raise
            count = (data.get("data") or {}).get("Count", 0) or 0
            modules = extract_modules(data, prefix)
            for m in modules:
                code = m["module_code"]
                if not code:
                    continue
                if should_keep(m, seen_codes):
                    if code in seen_codes:
                        old_idx = seen_codes[code]
                        all_modules[old_idx] = m
                    else:
                        seen_codes[code] = len(all_modules)
                        all_modules.append(m)
            print(f"  Page {page}: got {len(modules)} modules (total count: {count})")
            start += 500
            page += 1
            if start >= count:
                break
            time.sleep(0.3)

    print(f"\nTotal unique modules: {len(all_modules)}")

    # Enrich with school_abbr, url, active
    output = []
    for m in all_modules:
        code = m["module_code"]
        prefix = code[0].upper() if code else "X"
        school_name = m.get("school_name", "") or PREFIX_SCHOOL.get(prefix, "")
        school_abbr = get_school_abbr(school_name)
        output.append({
            "module_code": code,
            "module_name": m["module_name"],
            "synopsis": m["synopsis"],
            "school_name": school_name,
            "school_abbr": school_abbr,
            "url": f"https://www.rp.edu.sg/education/modules/{code.lower()}",
            "active": True,
        })

    json_path = os.path.join(script_dir, "rp_modules_synopsis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Written {json_path}")

    csv_path = os.path.join(script_dir, "rp_modules_synopsis.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "module_code", "module_name", "synopsis", "school_name", "school_abbr", "url", "active"
        ])
        writer.writeheader()
        writer.writerows(output)
    print(f"Written {csv_path}")


if __name__ == "__main__":
    main()

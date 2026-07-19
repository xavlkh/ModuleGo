#!/usr/bin/env python3
"""CLI entrypoint for upserting scraped data to Supabase.

Used by GitHub Actions after run_all.py completes.  Reads the JSON
files from app/static/local-data/data/ and upserts to Supabase.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'local-data', 'data')


def read_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def upsert_modules(sb, data):
    rows = [{
        'module_code': m['module_code'],
        'module_name': m.get('module_name', ''),
        'synopsis': m.get('synopsis', ''),
        'school_name': m.get('school_name', ''),
        'school_abbr': m.get('school_abbr', ''),
        'url': m.get('url', ''),
    } for m in data]
    sb.table('rp_modules').upsert(rows, on_conflict='module_code').execute()
    return len(rows)


def upsert_comparison(sb, data):
    rows = [{
        'module_code': r['module_code'],
        'summary': r.get('summary', ''),
        'suitable_for': r.get('suitable_for', ''),
    } for r in data]
    sb.table('rp_modules_comparision').upsert(rows, on_conflict='module_code').execute()
    return len(rows)


def upsert_courses(sb, data):
    module_keys = ['general_modules', 'major_modules', 'discipline_modules', 'elective_modules', 'industry_modules']
    rows = []
    for d in data:
        row = {
            'course_code': d.get('course_code', ''),
            'course_name': d.get('course_name', ''),
            'school_name': d.get('school_name', ''),
            'school_abbr': d.get('school_abbr', ''),
            'url': d.get('url', ''),
        }
        for key in module_keys:
            modules = d.get(key, [])
            row[key] = [m['code'] for m in modules if 'code' in m]
        rows.append(row)
    sb.table('rp_courses').upsert(rows, on_conflict='course_code').execute()
    return len(rows)


def main():
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SECRET_KEY')
    if not url or not key:
        sys.exit('SUPABASE_URL and SUPABASE_SECRET_KEY must be set.')

    sb = create_client(url, key)
    total = 0

    print('Upserting modules...')
    total += upsert_modules(sb, read_json('rp_modules_synopsis.json'))

    print('Upserting comparison...')
    total += upsert_comparison(sb, read_json('rp_modules_comparison.json'))

    print('Upserting courses...')
    total += upsert_courses(sb, read_json('rp_courses.json'))

    print(f'Done. {total} records upserted.')


if __name__ == '__main__':
    main()

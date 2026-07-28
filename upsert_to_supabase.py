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
from postgrest.exceptions import APIError
from supabase import create_client

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'local-data', 'data')

MINORS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rp_minors (
    id BIGSERIAL PRIMARY KEY,
    minor_name TEXT UNIQUE NOT NULL,
    minor_type TEXT NOT NULL,
    url TEXT DEFAULT '',
    modules JSONB DEFAULT '[]'::jsonb,
    eligibility TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE rp_minors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access" ON rp_minors
    FOR SELECT USING (true);

CREATE POLICY "Service role full access" ON rp_minors
    FOR ALL USING (auth.role() = 'service_role');
"""

CAREER_PATHS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rp_career_paths (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    keywords JSONB DEFAULT '[]'::jsonb,
    module_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE rp_career_paths ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access" ON rp_career_paths
    FOR SELECT USING (true);

CREATE POLICY "Service role full access" ON rp_career_paths
    FOR ALL USING (auth.role() = 'service_role');
"""


def read_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def table_exists(sb, table_name):
    try:
        sb.table(table_name).select('*').limit(0).execute()
        return True
    except APIError as e:
        return not ('does not exist' in str(e) or 'PGRST205' in str(e))


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
        # Store major groupings if present
        if 'major_groups' in d:
            row['major_groups'] = d['major_groups']
        rows.append(row)
    sb.table('rp_courses').upsert(rows, on_conflict='course_code').execute()
    return len(rows)


def upsert_minors(sb, data):
    rows = [{
        'minor_name': m['minor_name'],
        'minor_type': m.get('minor_type', ''),
        'url': m.get('url', ''),
        'modules': [{'code': mod['code'], 'name': mod['name']} for mod in m.get('modules', [])],
        'eligibility': m.get('eligibility', ''),
    } for m in data]
    sb.table('rp_minors').upsert(rows, on_conflict='minor_name').execute()
    return len(rows)


def upsert_career_paths(sb, data):
    rows = [{
        'id': p['id'],
        'label': p['label'],
        'keywords': p.get('keywords', []),
        'module_count': p.get('module_count', 0),
    } for p in data]
    sb.table('rp_career_paths').upsert(rows, on_conflict='id').execute()
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

    print('Upserting courses...')
    total += upsert_courses(sb, read_json('rp_courses.json'))

    if table_exists(sb, 'rp_minors'):
        print('Upserting minors...')
        total += upsert_minors(sb, read_json('rp_minors.json'))
    else:
        print('SKIP: rp_minors table does not exist.')
        print('Create it in Supabase SQL Editor with:')
        print(MINORS_TABLE_SQL)

    if table_exists(sb, 'rp_career_paths'):
        print('Upserting career paths...')
        total += upsert_career_paths(sb, read_json('rp_career_paths.json'))
    else:
        print('SKIP: rp_career_paths table does not exist.')
        print('Create it in Supabase SQL Editor with:')
        print(CAREER_PATHS_TABLE_SQL)

    print(f'Done. {total} records upserted.')


if __name__ == '__main__':
    main()

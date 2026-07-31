"""Seed local PostgreSQL with scraped module data.

Usage:
    DATABASE_URL=postgresql://modulego:modulego@postgres:5432/modulego python seed_db.py

Runs the scraping pipeline (if data files don't exist), then upserts
JSON data into the local PostgreSQL tables.
"""

import json
import os
import sys

import psycopg2
import psycopg2.extras

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


def read_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        sys.exit(f"Data file not found: {path}\nRun the scraper first.")
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def create_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rp_modules (
                module_code TEXT PRIMARY KEY,
                module_name TEXT DEFAULT '',
                synopsis TEXT DEFAULT '',
                school_name TEXT DEFAULT '',
                school_abbr TEXT DEFAULT '',
                url TEXT DEFAULT ''
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rp_courses (
                course_code TEXT PRIMARY KEY,
                course_name TEXT DEFAULT '',
                school_name TEXT DEFAULT '',
                school_abbr TEXT DEFAULT '',
                url TEXT DEFAULT '',
                general_modules JSONB DEFAULT '[]',
                major_modules JSONB DEFAULT '[]',
                discipline_modules JSONB DEFAULT '[]',
                elective_modules JSONB DEFAULT '[]',
                industry_modules JSONB DEFAULT '[]',
                major_groups JSONB DEFAULT '[]'
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rp_minors (
                minor_name TEXT PRIMARY KEY,
                minor_type TEXT DEFAULT '',
                url TEXT DEFAULT '',
                modules JSONB DEFAULT '[]',
                eligibility TEXT DEFAULT ''
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rp_career_paths (
                id TEXT PRIMARY KEY,
                label TEXT DEFAULT '',
                keywords JSONB DEFAULT '[]',
                module_count INTEGER DEFAULT 0
            );
        """)
        # Reviews table — matches spec schema (no auth.users FK for local PG)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                module_code TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                comment TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ,
                owner_token TEXT,
                user_id UUID,
                guest_owner_hash TEXT,
                is_anonymous BOOLEAN NOT NULL DEFAULT TRUE,
                author_display_name TEXT
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reviews_module_code ON reviews (module_code)")
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_reviews_account_module
                ON reviews (module_code, user_id) WHERE user_id IS NOT NULL
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_reviews_guest_module
                ON reviews (module_code, guest_owner_hash)
                WHERE guest_owner_hash IS NOT NULL
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS review_votes (
                id BIGSERIAL PRIMARY KEY,
                review_id BIGINT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
                owner_token TEXT,
                user_id UUID,
                guest_owner_hash TEXT,
                vote_type SMALLINT NOT NULL CHECK (vote_type IN (1, -1)),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_review_votes_review_id ON review_votes (review_id)")
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_votes_account_review
                ON review_votes (review_id, user_id) WHERE user_id IS NOT NULL
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_votes_guest_review
                ON review_votes (review_id, guest_owner_hash)
                WHERE guest_owner_hash IS NOT NULL
        """)
    conn.commit()


def upsert_modules(conn, data):
    with conn.cursor() as cur:
        for m in data:
            cur.execute("""
                INSERT INTO rp_modules (module_code, module_name, synopsis, school_name, school_abbr, url)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (module_code) DO UPDATE SET
                    module_name = EXCLUDED.module_name,
                    synopsis = EXCLUDED.synopsis,
                    school_name = EXCLUDED.school_name,
                    school_abbr = EXCLUDED.school_abbr,
                    url = EXCLUDED.url
            """, (
                m['module_code'],
                m.get('module_name', ''),
                m.get('synopsis', ''),
                m.get('school_name', ''),
                m.get('school_abbr', ''),
                m.get('url', ''),
            ))
    conn.commit()
    return len(data)


def upsert_courses(conn, data):
    module_keys = ['general_modules', 'major_modules', 'discipline_modules', 'elective_modules', 'industry_modules']
    with conn.cursor() as cur:
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
                row[key] = psycopg2.extras.Json([m['code'] for m in modules if 'code' in m])
            if 'major_groups' in d:
                row['major_groups'] = psycopg2.extras.Json(d['major_groups'])
            else:
                row['major_groups'] = psycopg2.extras.Json([])
            cur.execute("""
                INSERT INTO rp_courses (course_code, course_name, school_name, school_abbr, url,
                    general_modules, major_modules, discipline_modules, elective_modules, industry_modules, major_groups)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (course_code) DO UPDATE SET
                    course_name = EXCLUDED.course_name,
                    school_name = EXCLUDED.school_name,
                    school_abbr = EXCLUDED.school_abbr,
                    url = EXCLUDED.url,
                    general_modules = EXCLUDED.general_modules,
                    major_modules = EXCLUDED.major_modules,
                    discipline_modules = EXCLUDED.discipline_modules,
                    elective_modules = EXCLUDED.elective_modules,
                    industry_modules = EXCLUDED.industry_modules,
                    major_groups = EXCLUDED.major_groups
            """, (
                row['course_code'], row['course_name'], row['school_name'],
                row['school_abbr'], row['url'], row['general_modules'],
                row['major_modules'], row['discipline_modules'],
                row['elective_modules'], row['industry_modules'], row['major_groups'],
            ))
    conn.commit()
    return len(data)


def upsert_minors(conn, data):
    with conn.cursor() as cur:
        for m in data:
            cur.execute("""
                INSERT INTO rp_minors (minor_name, minor_type, url, modules, eligibility)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (minor_name) DO UPDATE SET
                    minor_type = EXCLUDED.minor_type,
                    url = EXCLUDED.url,
                    modules = EXCLUDED.modules,
                    eligibility = EXCLUDED.eligibility
            """, (
                m['minor_name'],
                m.get('minor_type', ''),
                m.get('url', ''),
                psycopg2.extras.Json([{'code': mod['code'], 'name': mod['name']} for mod in m.get('modules', [])]),
                m.get('eligibility', ''),
            ))
    conn.commit()
    return len(data)


def upsert_career_paths(conn, data):
    with conn.cursor() as cur:
        for p in data:
            cur.execute("""
                INSERT INTO rp_career_paths (id, label, keywords, module_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    label = EXCLUDED.label,
                    keywords = EXCLUDED.keywords,
                    module_count = EXCLUDED.module_count
            """, (
                p['id'],
                p['label'],
                psycopg2.extras.Json(p.get('keywords', [])),
                p.get('module_count', 0),
            ))
    conn.commit()
    return len(data)


def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        sys.exit('DATABASE_URL must be set.')

    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(db_url)

    print("Creating tables...")
    create_tables(conn)

    total = 0

    print("Upserting modules...")
    total += upsert_modules(conn, read_json('rp_modules_synopsis.json'))

    print("Upserting courses...")
    total += upsert_courses(conn, read_json('rp_courses.json'))

    minors_file = os.path.join(DATA_DIR, 'rp_minors.json')
    if os.path.exists(minors_file):
        print("Upserting minors...")
        total += upsert_minors(conn, read_json('rp_minors.json'))
    else:
        print("SKIP: rp_minors.json not found.")

    career_file = os.path.join(DATA_DIR, 'rp_career_paths.json')
    if os.path.exists(career_file):
        print("Upserting career paths...")
        total += upsert_career_paths(conn, read_json('rp_career_paths.json'))
    else:
        print("SKIP: rp_career_paths.json not found.")

    conn.close()
    print(f"Done. {total} records upserted.")


if __name__ == '__main__':
    main()

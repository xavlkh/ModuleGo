"""ModuleGo Flask application.

Provides the backend API for module data and review management,
serving Republic Polytechnic students.
"""
import json
import os
import re
import sqlite3
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from auth_routes import auth_bp
from db import (
    public_review,
    review_to_dict,
    select_review,
)
from ownership import (
    current_guest_hash,
    identity_owns,
    request_identity,
    rotate_guest_cookie,
    set_pending_guest_cookie,
)

load_dotenv()

app = Flask(__name__,
            static_folder='app/static',
            template_folder='app/templates')
app.config.update(
    SECRET_KEY=os.environ.get(
        'FLASK_SECRET_KEY',
        'modulego-local-development-secret-change-me',
    ),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=30 * 24 * 60 * 60,
)
app.register_blueprint(auth_bp)
app.after_request(set_pending_guest_cookie)

csrf = CSRFProtect()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'error'


@login_manager.user_loader
def load_user(user_id):
    from user_model import User
    return User.find_by_id(user_id)


_test_request_counter = 0


def _rate_limit_key():
    """Return a unique key per request. In testing, use a unique key per
    request so rate limits don't accumulate across test methods."""
    if app.config.get('TESTING'):
        global _test_request_counter
        _test_request_counter += 1
        return f"test-{_test_request_counter}"
    return get_remote_address()


limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=["200 per hour"],
    storage_uri="memory://",
)

_base_dir = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(_base_dir, 'app', 'static', 'local-data', 'data')
MAX_COMMENT_LENGTH = 500
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.1-flash-lite')
GEMINI_TIMEOUT_SECONDS = 25
MAX_COMPARISON_SOURCE_LENGTH = 4000
_CAREER_PATHS_TABLE = 'rp_career_paths'


class GeminiServiceError(RuntimeError):
    """Raised when Gemini cannot return a valid comparison."""


db_name = os.environ.get('DATABASE_PATH', os.path.join(_base_dir, 'modulego.db'))
database_url = os.environ.get('DATABASE_URL')

csrf.init_app(app)
limiter.init_app(app)


def _get_commit_hash() -> str | None:
    """Return the short git commit hash, or None if unavailable."""
    # Environment variable override (set in .env on EC2)
    env_hash = os.environ.get('COMMIT_HASH', '').strip()
    if env_hash:
        return env_hash[:7]
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, cwd=_base_dir, timeout=5, check=False
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


@app.context_processor
def inject_globals():
    """Inject global template variables into all Jinja templates."""
    return {
        'current_year': datetime.now(timezone.utc).year,
        'commit_hash': _get_commit_hash(),
    }


def get_db() -> sqlite3.Connection:
    """Open a local review database connection with dictionary-like rows."""
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def database_connection():
    """Provide a transactional database connection scope."""
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def use_sqlite_reviews() -> bool:
    """Return True when SQLite should be used (tests or no PostgreSQL)."""
    if app.config.get('TESTING'):
        return True
    return not database_url


def use_postgres() -> bool:
    """Return True when PostgreSQL should be used (DATABASE_URL set, not testing)."""
    if app.config.get('TESTING'):
        return False
    return bool(database_url)


def get_pg_db():
    """Open a PostgreSQL connection with dict-like row access."""
    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    return conn


@contextmanager
def pg_connection():
    """Provide a transactional PostgreSQL connection scope."""
    conn = get_pg_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()



def init_db() -> None:
    """Create or upgrade the SQLite review + career_paths tables."""
    with database_connection() as conn:
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS REVIEWS
               (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                MODULE_CODE TEXT NOT NULL,
                RATING INTEGER NOT NULL,
                COMMENT TEXT NOT NULL DEFAULT '',
                CREATED_AT DATETIME DEFAULT CURRENT_TIMESTAMP,
                UPDATED_AT DATETIME,
                USER_ID TEXT,
                GUEST_OWNER_HASH TEXT,
                IS_ANONYMOUS INTEGER NOT NULL DEFAULT 1,
                AUTHOR_DISPLAY_NAME TEXT)'''
        )
        columns = {
            row['name']
            for row in conn.execute('PRAGMA table_info(REVIEWS)').fetchall()
        }
        if 'UPDATED_AT' not in columns:
            conn.execute('ALTER TABLE REVIEWS ADD COLUMN UPDATED_AT DATETIME')
        if 'USER_ID' not in columns:
            conn.execute('ALTER TABLE REVIEWS ADD COLUMN USER_ID TEXT')
        if 'GUEST_OWNER_HASH' not in columns:
            conn.execute('ALTER TABLE REVIEWS ADD COLUMN GUEST_OWNER_HASH TEXT')
        if 'IS_ANONYMOUS' not in columns:
            conn.execute(
                'ALTER TABLE REVIEWS ADD COLUMN IS_ANONYMOUS INTEGER '
                'NOT NULL DEFAULT 1'
            )
        if 'AUTHOR_DISPLAY_NAME' not in columns:
            conn.execute(
                'ALTER TABLE REVIEWS ADD COLUMN AUTHOR_DISPLAY_NAME TEXT'
            )
        conn.execute(
            'CREATE INDEX IF NOT EXISTS IDX_REVIEWS_MODULE_CODE '
            'ON REVIEWS (MODULE_CODE)'
        )
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS REVIEW_VOTES
               (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                REVIEW_ID INTEGER NOT NULL,
                USER_ID TEXT,
                GUEST_OWNER_HASH TEXT,
                VOTE_TYPE INTEGER NOT NULL CHECK (VOTE_TYPE IN (1, -1)),
                CREATED_AT DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (REVIEW_ID) REFERENCES REVIEWS(ID) ON DELETE CASCADE)'''
        )
        vote_columns = {
            row['name']
            for row in conn.execute('PRAGMA table_info(REVIEW_VOTES)').fetchall()
        }
        if 'USER_ID' not in vote_columns:
            conn.execute('ALTER TABLE REVIEW_VOTES ADD COLUMN USER_ID TEXT')
        if 'GUEST_OWNER_HASH' not in vote_columns:
            conn.execute(
                'ALTER TABLE REVIEW_VOTES ADD COLUMN GUEST_OWNER_HASH TEXT'
            )
        conn.execute(
            'CREATE INDEX IF NOT EXISTS IDX_REVIEW_VOTES_REVIEW_ID '
            'ON REVIEW_VOTES (REVIEW_ID)'
        )
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS '
            'UQ_REVIEWS_ACCOUNT_MODULE ON REVIEWS (MODULE_CODE, USER_ID) '
            'WHERE USER_ID IS NOT NULL'
        )
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS '
            'UQ_REVIEWS_GUEST_MODULE ON REVIEWS '
            '(MODULE_CODE, GUEST_OWNER_HASH) '
            'WHERE GUEST_OWNER_HASH IS NOT NULL'
        )
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS '
            'UQ_VOTES_ACCOUNT_REVIEW ON REVIEW_VOTES (REVIEW_ID, USER_ID) '
            'WHERE USER_ID IS NOT NULL'
        )
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS '
            'UQ_VOTES_GUEST_REVIEW ON REVIEW_VOTES '
            '(REVIEW_ID, GUEST_OWNER_HASH) '
            'WHERE GUEST_OWNER_HASH IS NOT NULL'
        )
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS BOOKMARKS
               (USER_ID TEXT NOT NULL,
                MODULE_CODE TEXT NOT NULL,
                CREATED_AT DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (USER_ID, MODULE_CODE))'''
        )
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS CAREER_PATHS
               (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                CAREER_ID TEXT NOT NULL UNIQUE,
                LABEL TEXT NOT NULL,
                KEYWORDS TEXT NOT NULL DEFAULT '[]')'''
        )
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS USERS
               (ID TEXT PRIMARY KEY,
                EMAIL TEXT NOT NULL UNIQUE,
                DISPLAY_NAME TEXT NOT NULL,
                PASSWORD_HASH TEXT NOT NULL,
                CREATED_AT DATETIME DEFAULT CURRENT_TIMESTAMP)'''
        )
    _seed_career_paths()
    _init_pg_users()


def _init_pg_users() -> None:
    """Create the users table in PostgreSQL if it doesn't exist."""
    if not use_postgres():
        return
    try:
        with pg_connection() as conn, conn.cursor() as cur:
            cur.execute(
                '''CREATE TABLE IF NOT EXISTS users
                   (id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW())'''
            )
        conn.commit()
    except psycopg2.Error:
        pass


def _load_career_paths_from_file() -> list | None:
    """Read career paths from local JSON file."""
    path = os.path.join(LOCAL_DATA_DIR, 'rp_career_paths.json')
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _seed_career_paths() -> None:
    """Seed career paths from local JSON into SQLite if table is empty."""
    if not use_sqlite_reviews():
        return
    with database_connection() as conn:
        count = conn.execute('SELECT COUNT(*) FROM CAREER_PATHS').fetchone()[0]
        if count > 0:
            return
    paths = _load_career_paths_from_file()
    if not paths:
        return
    with database_connection() as conn:
        for p in paths:
            try:
                conn.execute(
                    'INSERT INTO CAREER_PATHS (CAREER_ID, LABEL, KEYWORDS) VALUES (?, ?, ?)',
                    (p['id'], p['label'], json.dumps(p.get('keywords', [])))
                )
            except sqlite3.Error:
                continue


def init_pg_db() -> None:
    """Create the PostgreSQL review + career_paths tables."""
    with pg_connection() as conn, conn.cursor() as cur:
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS REVIEWS
               (ID SERIAL PRIMARY KEY,
                MODULE_CODE TEXT NOT NULL,
                RATING INTEGER NOT NULL,
                COMMENT TEXT NOT NULL DEFAULT '',
                CREATED_AT TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UPDATED_AT TIMESTAMPTZ,
                USER_ID UUID,
                GUEST_OWNER_HASH TEXT,
                IS_ANONYMOUS BOOLEAN NOT NULL DEFAULT TRUE,
                AUTHOR_DISPLAY_NAME TEXT)'''
        )
        cur.execute('ALTER TABLE REVIEWS ADD COLUMN IF NOT EXISTS USER_ID UUID')
        cur.execute(
            'ALTER TABLE REVIEWS ADD COLUMN IF NOT EXISTS '
            'GUEST_OWNER_HASH TEXT'
        )
        cur.execute(
            'ALTER TABLE REVIEWS ADD COLUMN IF NOT EXISTS '
            'IS_ANONYMOUS BOOLEAN NOT NULL DEFAULT TRUE'
        )
        cur.execute(
            'ALTER TABLE REVIEWS ADD COLUMN IF NOT EXISTS '
            'AUTHOR_DISPLAY_NAME TEXT'
        )
        cur.execute(
            'CREATE INDEX IF NOT EXISTS IDX_REVIEWS_MODULE_CODE ON REVIEWS (MODULE_CODE)'
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS REVIEW_VOTES
               (ID SERIAL PRIMARY KEY,
                REVIEW_ID INTEGER NOT NULL,
                USER_ID UUID,
                GUEST_OWNER_HASH TEXT,
                VOTE_TYPE INTEGER NOT NULL CHECK (VOTE_TYPE IN (1, -1)),
                CREATED_AT TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (REVIEW_ID) REFERENCES REVIEWS(ID) ON DELETE CASCADE)'''
        )
        cur.execute(
            'ALTER TABLE REVIEW_VOTES ADD COLUMN IF NOT EXISTS USER_ID UUID'
        )
        cur.execute(
            'ALTER TABLE REVIEW_VOTES ADD COLUMN IF NOT EXISTS '
            'GUEST_OWNER_HASH TEXT'
        )
        cur.execute(
            'CREATE INDEX IF NOT EXISTS IDX_REVIEW_VOTES_REVIEW_ID ON REVIEW_VOTES (REVIEW_ID)'
        )
        cur.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS UQ_REVIEWS_ACCOUNT_MODULE '
            'ON REVIEWS (MODULE_CODE, USER_ID) WHERE USER_ID IS NOT NULL'
        )
        cur.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS UQ_REVIEWS_GUEST_MODULE '
            'ON REVIEWS (MODULE_CODE, GUEST_OWNER_HASH) '
            'WHERE GUEST_OWNER_HASH IS NOT NULL'
        )
        cur.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS UQ_VOTES_ACCOUNT_REVIEW '
            'ON REVIEW_VOTES (REVIEW_ID, USER_ID) WHERE USER_ID IS NOT NULL'
        )
        cur.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS UQ_VOTES_GUEST_REVIEW '
            'ON REVIEW_VOTES (REVIEW_ID, GUEST_OWNER_HASH) '
            'WHERE GUEST_OWNER_HASH IS NOT NULL'
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS BOOKMARKS
               (USER_ID UUID NOT NULL,
                MODULE_CODE TEXT NOT NULL,
                CREATED_AT TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (USER_ID, MODULE_CODE))'''
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS rp_career_paths
               (ID SERIAL PRIMARY KEY,
                CAREER_ID TEXT NOT NULL UNIQUE,
                LABEL TEXT NOT NULL,
                KEYWORDS TEXT NOT NULL DEFAULT '[]')'''
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS RP_MODULES
               (MODULE_CODE TEXT PRIMARY KEY,
                MODULE_NAME TEXT DEFAULT '',
                SYNOPSIS TEXT DEFAULT '',
                SCHOOL_NAME TEXT DEFAULT '',
                SCHOOL_ABBR TEXT DEFAULT '',
                URL TEXT DEFAULT '')'''
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS RP_COURSES
               (COURSE_CODE TEXT PRIMARY KEY,
                COURSE_NAME TEXT DEFAULT '',
                SCHOOL_NAME TEXT DEFAULT '',
                SCHOOL_ABBR TEXT DEFAULT '',
                URL TEXT DEFAULT '',
                GENERAL_MODULES JSONB DEFAULT '[]',
                MAJOR_MODULES JSONB DEFAULT '[]',
                DISCIPLINE_MODULES JSONB DEFAULT '[]',
                ELECTIVE_MODULES JSONB DEFAULT '[]',
                INDUSTRY_MODULES JSONB DEFAULT '[]',
                MAJOR_GROUPS JSONB DEFAULT '[]')'''
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS RP_MINORS
               (MINOR_NAME TEXT PRIMARY KEY,
                MINOR_TYPE TEXT DEFAULT '',
                URL TEXT DEFAULT '',
                MODULES JSONB DEFAULT '[]',
                ELIGIBILITY TEXT DEFAULT '')'''
        )
    _init_pg_users()
    _seed_pg_career_paths()
    _seed_pg_modules()
    _seed_pg_courses()
    _seed_pg_minors()
    _sync_pg_sequences()


def _seed_pg_career_paths() -> None:
    """Seed career paths from local JSON into PostgreSQL if table is empty."""
    with pg_connection() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM {_CAREER_PATHS_TABLE}')
        count = cur.fetchone()[0]
        if count > 0:
            return
    paths = _load_career_paths_from_file()
    if not paths:
        return
    with pg_connection() as conn, conn.cursor() as cur:
        for p in paths:
            try:
                cur.execute(
                    f'INSERT INTO {_CAREER_PATHS_TABLE} (CAREER_ID, LABEL, KEYWORDS) VALUES (%s, %s, %s)',
                    (p['id'], p['label'], json.dumps(p.get('keywords', [])))
                )
            except psycopg2.Error:
                continue


def _seed_pg_modules() -> None:
    """Seed modules from local JSON into PostgreSQL if table is empty."""
    with pg_connection() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM RP_MODULES')
        if cur.fetchone()[0] > 0:
            return
    path = os.path.join(_LOCAL_DATA_DIR, 'rp_modules_synopsis.json')
    try:
        with open(path, encoding='utf-8') as f:
            modules = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    with pg_connection() as conn, conn.cursor() as cur:
        for m in modules:
            try:
                cur.execute(
                    'INSERT INTO RP_MODULES (MODULE_CODE, MODULE_NAME, SYNOPSIS, SCHOOL_NAME, SCHOOL_ABBR, URL) '
                    'VALUES (%s, %s, %s, %s, %s, %s)',
                    (m['module_code'], m.get('module_name', ''), m.get('synopsis', ''),
                     m.get('school_name', ''), m.get('school_abbr', ''), m.get('url', ''))
                )
            except psycopg2.Error:
                continue


def _seed_pg_courses() -> None:
    """Seed courses from local JSON into PostgreSQL if table is empty."""
    with pg_connection() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM RP_COURSES')
        if cur.fetchone()[0] > 0:
            return
    path = os.path.join(_LOCAL_DATA_DIR, 'rp_courses.json')
    try:
        with open(path, encoding='utf-8') as f:
            courses = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    module_keys = ['general_modules', 'major_modules', 'discipline_modules', 'elective_modules', 'industry_modules']
    with pg_connection() as conn, conn.cursor() as cur:
        for d in courses:
            try:
                row = {
                    'course_code': d.get('course_code', ''),
                    'course_name': d.get('course_name', ''),
                    'school_name': d.get('school_name', ''),
                    'school_abbr': d.get('school_abbr', ''),
                    'url': d.get('url', ''),
                }
                for key in module_keys:
                    row[key] = json.dumps([m['code'] for m in d.get(key, []) if 'code' in m])
                row['major_groups'] = json.dumps(d.get('major_groups', []))
                cur.execute(
                    'INSERT INTO RP_COURSES (COURSE_CODE, COURSE_NAME, SCHOOL_NAME, SCHOOL_ABBR, URL, '
                    'GENERAL_MODULES, MAJOR_MODULES, DISCIPLINE_MODULES, ELECTIVE_MODULES, INDUSTRY_MODULES, MAJOR_GROUPS) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (row['course_code'], row['course_name'], row['school_name'],
                     row['school_abbr'], row['url'], row['general_modules'],
                     row['major_modules'], row['discipline_modules'],
                     row['elective_modules'], row['industry_modules'], row['major_groups'])
                )
            except psycopg2.Error:
                continue


def _seed_pg_minors() -> None:
    """Seed minor programmes from local JSON into PostgreSQL if table is empty."""
    with pg_connection() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM RP_MINORS')
        if cur.fetchone()[0] > 0:
            return
    path = os.path.join(_LOCAL_DATA_DIR, 'rp_minors.json')
    try:
        with open(path, encoding='utf-8') as f:
            minors = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    with pg_connection() as conn, conn.cursor() as cur:
        for m in minors:
            try:
                cur.execute(
                    'INSERT INTO RP_MINORS (MINOR_NAME, MINOR_TYPE, URL, MODULES, ELIGIBILITY) '
                    'VALUES (%s, %s, %s, %s, %s)',
                    (m['minor_name'], m.get('minor_type', ''), m.get('url', ''),
                     json.dumps([{'code': mod['code'], 'name': mod['name']} for mod in m.get('modules', [])]),
                     m.get('eligibility', ''))
                )
            except psycopg2.Error:
                continue


def _sync_pg_sequences() -> None:
    """Reset PostgreSQL serial sequences to MAX(id) to prevent duplicate key errors."""
    tables = ['reviews', 'review_votes', 'rp_career_paths']
    with pg_connection() as conn, conn.cursor() as cur:
        for table in tables:
            try:
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"(SELECT COALESCE(MAX(id), 0) FROM {table}))"
                )
            except psycopg2.Error:
                continue


if use_sqlite_reviews():
    init_db()
elif use_postgres():
    init_pg_db()


class ReviewRepository:
    """Handles review persistence for SQLite and PostgreSQL."""

    @staticmethod
    def list_all(identity=None) -> list:
        """Return public reviews ordered by creation date descending."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                rows = conn.execute(
                    '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT,
                              UPDATED_AT, USER_ID,
                              GUEST_OWNER_HASH, IS_ANONYMOUS,
                              AUTHOR_DISPLAY_NAME
                       FROM REVIEWS ORDER BY CREATED_AT DESC, ID DESC'''
                ).fetchall()
            return [public_review(row, identity) for row in rows]

        with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT,
                          UPDATED_AT, USER_ID,
                          GUEST_OWNER_HASH, IS_ANONYMOUS,
                          AUTHOR_DISPLAY_NAME
                   FROM REVIEWS ORDER BY CREATED_AT DESC, ID DESC'''
            )
            rows = cur.fetchall()
        return [public_review(row, identity) for row in rows]

    @staticmethod
    def list_by_module(module_code: str, identity=None) -> list:
        """Return public reviews for one module code."""
        normalized = module_code.strip().upper()
        if use_sqlite_reviews():
            with database_connection() as conn:
                rows = conn.execute(
                    '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT,
                              UPDATED_AT, USER_ID,
                              GUEST_OWNER_HASH, IS_ANONYMOUS,
                              AUTHOR_DISPLAY_NAME
                       FROM REVIEWS WHERE MODULE_CODE = ?
                       ORDER BY CREATED_AT DESC, ID DESC''',
                    (normalized,),
                ).fetchall()
            return [public_review(row, identity) for row in rows]

        with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT,
                          UPDATED_AT, USER_ID,
                          GUEST_OWNER_HASH, IS_ANONYMOUS,
                          AUTHOR_DISPLAY_NAME
                   FROM REVIEWS WHERE MODULE_CODE = %s
                   ORDER BY CREATED_AT DESC, ID DESC''',
                (normalized,),
            )
            rows = cur.fetchall()
        return [public_review(row, identity) for row in rows]

    @staticmethod
    def create(payload: dict, identity: dict) -> tuple:
        """Create a new review. Returns (review_dict, error_response)."""
        ownership = {
            'user_id': identity.get('user_id'),
            'guest_owner_hash': identity.get('guest_owner_hash'),
        }
        is_anonymous = (
            True if identity['kind'] == 'guest'
            else bool(payload.get('is_anonymous', True))
        )
        author_name = (
            identity.get('display_name')
            if identity['kind'] == 'account'
            else None
        )

        try:
            if use_sqlite_reviews():
                with database_connection() as conn:
                    cursor = conn.execute(
                        '''INSERT INTO REVIEWS
                           (MODULE_CODE, RATING, COMMENT, USER_ID,
                            GUEST_OWNER_HASH, IS_ANONYMOUS,
                            AUTHOR_DISPLAY_NAME)
                           VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (
                            payload['module_code'], payload['rating'],
                            payload['comment'], ownership['user_id'],
                            ownership['guest_owner_hash'], int(is_anonymous),
                            author_name,
                        ),
                    )
                    row = select_review(conn, cursor.lastrowid)
                return public_review(row, identity), None

            with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    '''INSERT INTO REVIEWS
                       (MODULE_CODE, RATING, COMMENT, USER_ID,
                        GUEST_OWNER_HASH, IS_ANONYMOUS,
                        AUTHOR_DISPLAY_NAME)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       RETURNING *''',
                    (
                        payload['module_code'], payload['rating'],
                        payload['comment'], ownership['user_id'],
                        ownership['guest_owner_hash'], is_anonymous,
                        author_name,
                    ),
                )
                row = cur.fetchone()
            return public_review(row, identity), None
        except (sqlite3.IntegrityError, psycopg2.IntegrityError) as error:
            if 'unique' in str(error).lower():
                return None, (jsonify({
                    'error': 'You already reviewed this module.',
                }), 409)
            raise

    @staticmethod
    def update(review_id: int, payload: dict, identity: dict) -> tuple:
        """Update an existing review. Returns (review_dict, error_response)."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                existing = conn.execute(
                    'SELECT * FROM REVIEWS WHERE ID = ?', (review_id,)
                ).fetchone()
                if not existing:
                    return None, (jsonify({'error': 'Review not found.'}), 404)
                if not identity_owns(review_to_dict(existing), identity):
                    return None, (jsonify({'error': 'Forbidden: you do not own this review.'}), 403)
                anonymous = (
                    True if identity['kind'] == 'guest'
                    else bool(payload.get(
                        'is_anonymous',
                        review_to_dict(existing)['is_anonymous'],
                    ))
                )
                if (identity['kind'] == 'account'
                        and not existing['USER_ID']
                        and existing['GUEST_OWNER_HASH']):
                    conn.execute(
                        '''UPDATE REVIEWS
                           SET USER_ID = ?, GUEST_OWNER_HASH = NULL,
                               AUTHOR_DISPLAY_NAME = ?
                           WHERE ID = ?''',
                        (identity['user_id'], identity.get('display_name'), review_id),
                    )
                conn.execute(
                    '''UPDATE REVIEWS
                       SET RATING = ?, COMMENT = ?, IS_ANONYMOUS = ?,
                           UPDATED_AT = CURRENT_TIMESTAMP
                       WHERE ID = ?''',
                    (
                        payload['rating'], payload['comment'], int(anonymous),
                        review_id,
                    ),
                )
                row = select_review(conn, review_id)
            return public_review(row, identity), None

        with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM REVIEWS WHERE ID = %s', (review_id,))
            existing = cur.fetchone()
            if not existing:
                return None, (jsonify({'error': 'Review not found.'}), 404)
            if not identity_owns(review_to_dict(existing), identity):
                return None, (jsonify({'error': 'Forbidden: you do not own this review.'}), 403)
            anonymous = (
                True if identity['kind'] == 'guest'
                else bool(payload.get(
                    'is_anonymous',
                    review_to_dict(existing)['is_anonymous'],
                ))
            )
            if (identity['kind'] == 'account'
                    and not existing['user_id']
                    and existing['guest_owner_hash']):
                cur.execute(
                    '''UPDATE REVIEWS
                       SET user_id = %s, guest_owner_hash = NULL,
                           author_display_name = %s
                       WHERE id = %s''',
                    (identity['user_id'], identity.get('display_name'), review_id),
                )
            cur.execute(
                '''UPDATE REVIEWS
                   SET RATING = %s, COMMENT = %s, IS_ANONYMOUS = %s,
                       UPDATED_AT = CURRENT_TIMESTAMP
                   WHERE ID = %s''',
                (
                    payload['rating'], payload['comment'], anonymous,
                    review_id,
                ),
            )
            cur.execute('SELECT * FROM REVIEWS WHERE ID = %s', (review_id,))
            row = cur.fetchone()
        return public_review(row, identity), None

    @staticmethod
    def delete(review_id: int, identity: dict) -> tuple | None:
        """Delete a review. Returns None on success or error response."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                existing = conn.execute(
                    'SELECT * FROM REVIEWS WHERE ID = ?', (review_id,)
                ).fetchone()
                if not existing:
                    return jsonify({'error': 'Review not found.'}), 404
                if not identity_owns(review_to_dict(existing), identity):
                    return jsonify({'error': 'Forbidden: you do not own this review.'}), 403
                conn.execute('DELETE FROM REVIEWS WHERE ID = ?', (review_id,))
            return None

        with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM REVIEWS WHERE ID = %s', (review_id,))
            existing = cur.fetchone()
            if not existing:
                return jsonify({'error': 'Review not found.'}), 404
            if not identity_owns(review_to_dict(existing), identity):
                return jsonify({'error': 'Forbidden: you do not own this review.'}), 403
            cur.execute('DELETE FROM REVIEWS WHERE ID = %s', (review_id,))
        return None

    @staticmethod
    def update_author_display_name(user_id: str, display_name: str) -> int:
        """Update the stored author name for every review owned by an account."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                cursor = conn.execute(
                    '''UPDATE REVIEWS
                       SET AUTHOR_DISPLAY_NAME = ?
                       WHERE USER_ID = ?''',
                    (display_name, user_id),
                )
                return cursor.rowcount

        with pg_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    '''UPDATE REVIEWS
                       SET AUTHOR_DISPLAY_NAME = %s
                       WHERE USER_ID = %s''',
                    (display_name, user_id),
                )
                return cur.rowcount

    @staticmethod
    def count_by_user(user_id: str) -> int:
        """Count reviews authored by a specific user account."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                row = conn.execute(
                    'SELECT COUNT(*) as cnt FROM REVIEWS WHERE USER_ID = ?',
                    (user_id,),
                ).fetchone()
            return row['cnt']

        with pg_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    'SELECT COUNT(*) FROM REVIEWS WHERE USER_ID = %s',
                    (user_id,),
                )
                return cur.fetchone()[0]

    @staticmethod
    def rating_summaries() -> dict:
        """Return average, review count, and rating distribution per module."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                rows = conn.execute(
                    '''SELECT MODULE_CODE,
                              ROUND(AVG(RATING), 2) AS AVERAGE_RATING,
                              COUNT(*) AS REVIEW_COUNT,
                              SUM(CASE WHEN RATING = 5 THEN 1 ELSE 0 END) AS RATING_5_COUNT,
                              SUM(CASE WHEN RATING = 4 THEN 1 ELSE 0 END) AS RATING_4_COUNT,
                              SUM(CASE WHEN RATING = 3 THEN 1 ELSE 0 END) AS RATING_3_COUNT,
                              SUM(CASE WHEN RATING = 2 THEN 1 ELSE 0 END) AS RATING_2_COUNT,
                              SUM(CASE WHEN RATING = 1 THEN 1 ELSE 0 END) AS RATING_1_COUNT
                       FROM REVIEWS GROUP BY MODULE_CODE ORDER BY MODULE_CODE'''
                ).fetchall()
            return {
                row['MODULE_CODE']: {
                    'average_rating': row['AVERAGE_RATING'],
                    'review_count': row['REVIEW_COUNT'],
                    'distribution': {
                        '5': row['RATING_5_COUNT'],
                        '4': row['RATING_4_COUNT'],
                        '3': row['RATING_3_COUNT'],
                        '2': row['RATING_2_COUNT'],
                        '1': row['RATING_1_COUNT'],
                    },
                }
                for row in rows
            }

        with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''SELECT MODULE_CODE,
                          ROUND(AVG(RATING)::numeric, 2) AS average_rating,
                          COUNT(*) AS review_count,
                          SUM(CASE WHEN RATING = 5 THEN 1 ELSE 0 END) AS rating_5_count,
                          SUM(CASE WHEN RATING = 4 THEN 1 ELSE 0 END) AS rating_4_count,
                          SUM(CASE WHEN RATING = 3 THEN 1 ELSE 0 END) AS rating_3_count,
                          SUM(CASE WHEN RATING = 2 THEN 1 ELSE 0 END) AS rating_2_count,
                          SUM(CASE WHEN RATING = 1 THEN 1 ELSE 0 END) AS rating_1_count
                   FROM REVIEWS GROUP BY MODULE_CODE ORDER BY MODULE_CODE'''
            )
            rows = cur.fetchall()
        return {
            row['module_code']: {
                'average_rating': float(row['average_rating']),
                'review_count': row['review_count'],
                'distribution': {
                    '5': row['rating_5_count'],
                    '4': row['rating_4_count'],
                    '3': row['rating_3_count'],
                    '2': row['rating_2_count'],
                    '1': row['rating_1_count'],
                },
            }
            for row in rows
        }


app.extensions['review_repository'] = ReviewRepository


class VoteRepository:
    """Handles vote persistence for SQLite and PostgreSQL."""

    @staticmethod
    def _identity_filter(identity):
        """Return the ownership column and value for an identity."""
        if not identity:
            return None, None
        if identity['kind'] == 'account':
            return 'user_id', identity['user_id']
        return 'guest_owner_hash', identity['guest_owner_hash']

    @staticmethod
    def get_votes(review_id: int, identity=None) -> dict:
        """Return total score and the request identity's vote."""
        return VoteRepository.get_votes_bulk([review_id], identity).get(
            review_id,
            {'score': 0, 'user_vote': 0},
        )

    @staticmethod
    def get_votes_bulk(review_ids: list, identity=None) -> dict:
        """Return vote scores for several reviews without exposing ownership."""
        if not review_ids:
            return {}
        column, value = VoteRepository._identity_filter(identity)
        scores = {}
        user_votes = {}

        if use_sqlite_reviews():
            placeholders = ','.join('?' * len(review_ids))
            with database_connection() as conn:
                rows = conn.execute(
                    f'''SELECT REVIEW_ID, COALESCE(SUM(VOTE_TYPE), 0) score
                        FROM REVIEW_VOTES
                        WHERE REVIEW_ID IN ({placeholders})
                        GROUP BY REVIEW_ID''',
                    review_ids,
                ).fetchall()
                scores = {row['REVIEW_ID']: row['score'] for row in rows}
                if column:
                    rows = conn.execute(
                        f'''SELECT REVIEW_ID, VOTE_TYPE FROM REVIEW_VOTES
                            WHERE REVIEW_ID IN ({placeholders})
                              AND {column.upper()} = ?''',
                        (*review_ids, value),
                    ).fetchall()
                    user_votes = {
                        row['REVIEW_ID']: row['VOTE_TYPE'] for row in rows
                    }
        else:
            placeholders = ','.join(['%s'] * len(review_ids))
            with pg_connection() as conn, conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cur:
                cur.execute(
                    f'''SELECT REVIEW_ID, COALESCE(SUM(VOTE_TYPE), 0) score
                        FROM REVIEW_VOTES
                        WHERE REVIEW_ID IN ({placeholders})
                        GROUP BY REVIEW_ID''',
                    review_ids,
                )
                scores = {row['review_id']: row['score'] for row in cur.fetchall()}
                if column:
                    cur.execute(
                        f'''SELECT REVIEW_ID, VOTE_TYPE FROM REVIEW_VOTES
                            WHERE REVIEW_ID IN ({placeholders})
                              AND {column} = %s''',
                        (*review_ids, value),
                    )
                    user_votes = {
                        row['review_id']: row['vote_type']
                        for row in cur.fetchall()
                    }

        return {
            review_id: {
                'score': scores.get(review_id, 0),
                'user_vote': user_votes.get(review_id, 0),
            }
            for review_id in review_ids
        }

    @staticmethod
    def _review_owned(review_id, identity):
        """Return whether the request identity wrote the target review."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                row = conn.execute(
                    'SELECT * FROM REVIEWS WHERE ID = ?',
                    (review_id,),
                ).fetchone()
        else:
            with pg_connection() as conn, conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cur:
                cur.execute('SELECT * FROM REVIEWS WHERE ID = %s', (review_id,))
                row = cur.fetchone()
        return row is not None and identity_owns(review_to_dict(row), identity)

    @staticmethod
    def vote(review_id: int, vote_type: int, identity: dict) -> tuple:
        """Toggle or change an owned account/guest vote."""
        if vote_type not in (1, -1):
            return None, (jsonify({
                'error': 'Vote type must be 1 or -1.',
            }), 400)
        if VoteRepository._review_owned(review_id, identity):
            return None, (jsonify({
                'error': 'You cannot vote on your own review.',
            }), 403)
        column, value = VoteRepository._identity_filter(identity)

        if use_sqlite_reviews():
            with database_connection() as conn:
                review = conn.execute(
                    'SELECT ID FROM REVIEWS WHERE ID = ?', (review_id,)
                ).fetchone()
                if not review:
                    return None, (jsonify({'error': 'Review not found.'}), 404)
                existing = conn.execute(
                    f'''SELECT ID, VOTE_TYPE FROM REVIEW_VOTES
                        WHERE REVIEW_ID = ? AND {column.upper()} = ?''',
                    (review_id, value),
                ).fetchone()
                return VoteRepository._write_sqlite_vote(
                    conn, existing, review_id, vote_type, column, value
                ), None

        with pg_connection() as conn, conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cur:
                cur.execute(
                    f'''SELECT ID, VOTE_TYPE FROM REVIEW_VOTES
                        WHERE REVIEW_ID = %s AND {column} = %s''',
                    (review_id, value),
                )
                existing = cur.fetchone()
                if existing:
                    if existing['vote_type'] == vote_type:
                        cur.execute(
                            'DELETE FROM REVIEW_VOTES WHERE ID = %s',
                            (existing['id'],),
                        )
                        return {'action': 'removed', 'vote_type': 0}, None
                    cur.execute(
                        'UPDATE REVIEW_VOTES SET VOTE_TYPE = %s WHERE ID = %s',
                        (vote_type, existing['id']),
                    )
                    return {'action': 'updated', 'vote_type': vote_type}, None
                cur.execute(
                    f'''INSERT INTO REVIEW_VOTES
                        (REVIEW_ID, {column}, VOTE_TYPE)
                        VALUES (%s, %s, %s)''',
                    (review_id, value, vote_type),
                )
                return {'action': 'added', 'vote_type': vote_type}, None

    @staticmethod
    def _write_sqlite_vote(
        conn, existing, review_id, vote_type, column, value
    ):
        """Apply SQLite vote toggle semantics."""
        if existing:
            if existing['VOTE_TYPE'] == vote_type:
                conn.execute(
                    'DELETE FROM REVIEW_VOTES WHERE ID = ?',
                    (existing['ID'],),
                )
                return {'action': 'removed', 'vote_type': 0}
            conn.execute(
                'UPDATE REVIEW_VOTES SET VOTE_TYPE = ? WHERE ID = ?',
                (vote_type, existing['ID']),
            )
            return {'action': 'updated', 'vote_type': vote_type}
        conn.execute(
            f'''INSERT INTO REVIEW_VOTES (REVIEW_ID, {column.upper()}, VOTE_TYPE)
                VALUES (?, ?, ?)''',
            (review_id, value, vote_type),
        )
        return {'action': 'added', 'vote_type': vote_type}

    @staticmethod
    def remove(review_id: int, identity: dict) -> None:
        """Remove the request identity's vote."""
        column, value = VoteRepository._identity_filter(identity)
        if use_sqlite_reviews():
            with database_connection() as conn:
                conn.execute(
                    f'''DELETE FROM REVIEW_VOTES
                        WHERE REVIEW_ID = ? AND {column.upper()} = ?''',
                    (review_id, value),
                )
        else:
            with pg_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    f'''DELETE FROM REVIEW_VOTES
                        WHERE REVIEW_ID = %s AND {column} = %s''',
                    (review_id, value),
                )


class BookmarkRepository:
    """Persist cross-device bookmarks for authenticated accounts."""

    @staticmethod
    def list_for_user(user_id):
        """Return an account's bookmark module codes."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                rows = conn.execute(
                    '''SELECT MODULE_CODE FROM BOOKMARKS
                       WHERE USER_ID = ? ORDER BY CREATED_AT''',
                    (user_id,),
                ).fetchall()
            return [row['MODULE_CODE'] for row in rows]
        with pg_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    '''SELECT MODULE_CODE FROM BOOKMARKS
                       WHERE USER_ID = %s ORDER BY CREATED_AT''',
                    (user_id,),
                )
                return [row[0] for row in cur.fetchall()]

    @staticmethod
    def add(user_id, module_code):
        """Add a bookmark idempotently."""
        code = module_code.strip().upper()
        if use_sqlite_reviews():
            with database_connection() as conn:
                conn.execute(
                    '''INSERT OR IGNORE INTO BOOKMARKS
                       (USER_ID, MODULE_CODE) VALUES (?, ?)''',
                    (user_id, code),
                )
        else:
            with pg_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    '''INSERT INTO BOOKMARKS (USER_ID, MODULE_CODE)
                       VALUES (%s, %s) ON CONFLICT DO NOTHING''',
                    (user_id, code),
                )
        return code, None

    @staticmethod
    def remove(user_id, module_code=None):
        """Remove one or every account bookmark."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                if module_code:
                    conn.execute(
                        '''DELETE FROM BOOKMARKS
                           WHERE USER_ID = ? AND MODULE_CODE = ?''',
                        (user_id, module_code.strip().upper()),
                    )
                else:
                    conn.execute(
                        'DELETE FROM BOOKMARKS WHERE USER_ID = ?',
                        (user_id,),
                    )
        else:
            with pg_connection() as conn, conn.cursor() as cur:
                if module_code:
                    cur.execute(
                        '''DELETE FROM BOOKMARKS
                           WHERE USER_ID = %s AND MODULE_CODE = %s''',
                        (user_id, module_code.strip().upper()),
                    )
                else:
                    cur.execute(
                        'DELETE FROM BOOKMARKS WHERE USER_ID = %s',
                        (user_id,),
                    )


class OwnershipRepository:
    """Inspect and explicitly claim signed guest activity."""

    @staticmethod
    def pending_counts(guest_hash):
        """Return guest reviews and votes eligible for claiming."""
        if not guest_hash:
            return {'reviews': 0, 'votes': 0}
        if use_sqlite_reviews():
            with database_connection() as conn:
                reviews = conn.execute(
                    '''SELECT COUNT(*) FROM REVIEWS
                       WHERE GUEST_OWNER_HASH = ?''',
                    (guest_hash,),
                ).fetchone()[0]
                votes = conn.execute(
                    '''SELECT COUNT(*) FROM REVIEW_VOTES
                       WHERE GUEST_OWNER_HASH = ?''',
                    (guest_hash,),
                ).fetchone()[0]
            return {'reviews': reviews, 'votes': votes}
        with pg_connection() as conn, conn.cursor() as cur:
            cur.execute(
                '''SELECT COUNT(*) FROM REVIEWS
                   WHERE GUEST_OWNER_HASH = %s''',
                (guest_hash,),
            )
            reviews = cur.fetchone()[0]
            cur.execute(
                '''SELECT COUNT(*) FROM REVIEW_VOTES
                   WHERE GUEST_OWNER_HASH = %s''',
                (guest_hash,),
            )
            votes = cur.fetchone()[0]
        return {'reviews': reviews, 'votes': votes}

    @staticmethod
    def claim(identity, guest_hash, bookmark_codes):
        """Claim guest rows; account rows win every conflict."""
        if not guest_hash:
            return {
                'claimed_reviews': 0,
                'legacy_reviews': 0,
                'claimed_votes': 0,
                'removed_votes': 0,
                'bookmarks': len(BookmarkRepository.list_for_user(
                    identity['user_id']
                )),
            }
        codes = sorted({
            str(code).strip().upper() for code in bookmark_codes
            if isinstance(code, str) and code.strip()
        })
        if use_sqlite_reviews():
            return OwnershipRepository._claim_sqlite(
                identity, guest_hash, codes
            )
        return OwnershipRepository._claim_postgres(
            identity, guest_hash, codes
        )

    @staticmethod
    def _claim_sqlite(identity, guest_hash, codes):
        """Run the test/local ownership claim in one SQLite transaction."""
        user_id = identity['user_id']
        with database_connection() as conn:
            conflicts = conn.execute(
                '''SELECT guest.ID FROM REVIEWS guest
                   JOIN REVIEWS account
                     ON account.MODULE_CODE = guest.MODULE_CODE
                    AND account.USER_ID = ?
                   WHERE guest.GUEST_OWNER_HASH = ?''',
                (user_id, guest_hash),
            ).fetchall()
            conflict_ids = [row['ID'] for row in conflicts]
            claimed_reviews = conn.execute(
                '''UPDATE REVIEWS
                   SET USER_ID = ?, GUEST_OWNER_HASH = NULL,
                       AUTHOR_DISPLAY_NAME = ?, IS_ANONYMOUS = 1
                   WHERE GUEST_OWNER_HASH = ?
                     AND MODULE_CODE NOT IN (
                         SELECT MODULE_CODE FROM REVIEWS
                         WHERE USER_ID = ?
                     )''',
                (
                    user_id, identity['display_name'], guest_hash, user_id,
                ),
            ).rowcount

            removed_votes = 0
            claimed_votes = 0
            guest_votes = conn.execute(
                '''SELECT ID, REVIEW_ID FROM REVIEW_VOTES
                   WHERE GUEST_OWNER_HASH = ?''',
                (guest_hash,),
            ).fetchall()
            for vote in guest_votes:
                account_vote = conn.execute(
                    '''SELECT 1 FROM REVIEW_VOTES
                       WHERE REVIEW_ID = ? AND USER_ID = ?''',
                    (vote['REVIEW_ID'], user_id),
                ).fetchone()
                own_review = conn.execute(
                    '''SELECT 1 FROM REVIEWS
                       WHERE ID = ? AND USER_ID = ?''',
                    (vote['REVIEW_ID'], user_id),
                ).fetchone()
                if account_vote or own_review:
                    conn.execute(
                        'DELETE FROM REVIEW_VOTES WHERE ID = ?',
                        (vote['ID'],),
                    )
                    removed_votes += 1
                else:
                    conn.execute(
                        '''UPDATE REVIEW_VOTES
                           SET USER_ID = ?, GUEST_OWNER_HASH = NULL
                           WHERE ID = ?''',
                        (user_id, vote['ID']),
                    )
                    claimed_votes += 1
            for code in codes:
                conn.execute(
                    '''INSERT OR IGNORE INTO BOOKMARKS
                       (USER_ID, MODULE_CODE) VALUES (?, ?)''',
                    (user_id, code),
                )
            bookmark_count = conn.execute(
                'SELECT COUNT(*) FROM BOOKMARKS WHERE USER_ID = ?',
                (user_id,),
            ).fetchone()[0]
        return {
            'claimed_reviews': claimed_reviews,
            'legacy_reviews': len(conflict_ids),
            'claimed_votes': claimed_votes,
            'removed_votes': removed_votes,
            'bookmarks': bookmark_count,
        }

    @staticmethod
    def _claim_postgres(identity, guest_hash, codes):
        """Call the same database function in direct PostgreSQL mode."""
        with pg_connection() as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT claim_guest_activity(%s, %s, %s, %s)',
                (
                    identity['user_id'], guest_hash,
                    identity['display_name'], codes,
                ),
            )
            return cur.fetchone()[0]


def validate_review_payload(data: dict | None, require_module_code: bool = False) -> tuple:
    """Validate and sanitize review payload data.

    Args:
        data: Dictionary containing review data.
        require_module_code: If True, module_code is required.

    Returns:
        Tuple of (validated_payload, error_message).
    """
    if not isinstance(data, dict):
        return None, 'A JSON request body is required.'

    rating = data.get('rating')
    if isinstance(rating, bool) or not isinstance(rating, int):
        return None, 'Rating must be an integer from 1 to 5.'
    if rating < 1 or rating > 5:
        return None, 'Rating must be between 1 and 5.'

    comment = data.get('comment', '')
    if comment is None:
        comment = ''
    if not isinstance(comment, str):
        return None, 'Comment must be text.'
    comment = comment.strip()
    if len(comment) > MAX_COMMENT_LENGTH:
        return None, f'Comment must be {MAX_COMMENT_LENGTH} characters or fewer.'

    payload = {'rating': rating, 'comment': comment}
    if 'is_anonymous' in data:
        if not isinstance(data['is_anonymous'], bool):
            return None, 'Anonymous visibility must be true or false.'
        payload['is_anonymous'] = data['is_anonymous']
    if require_module_code:
        module_code = data.get('module_code')
        if not isinstance(module_code, str) or not module_code.strip():
            return None, 'Module code is required.'
        module_code = module_code.strip().upper()
        if len(module_code) > 20:
            return None, 'Module code is too long.'
        payload['module_code'] = module_code

    return payload, None


def validate_comparison_payload(data: dict | None) -> tuple:
    """Validate a request containing exactly two distinct module codes."""
    if not isinstance(data, dict):
        return None, 'A JSON request body is required.'

    module_codes = data.get('module_codes')
    if not isinstance(module_codes, list) or len(module_codes) != 2:
        return None, 'Exactly two module codes are required.'

    normalized_codes = []
    for code in module_codes:
        if not isinstance(code, str) or not code.strip():
            return None, 'Each module code must be non-empty text.'
        normalized_code = code.strip().upper()
        if len(normalized_code) > 20:
            return None, 'Module code is too long.'
        normalized_codes.append(normalized_code)

    if normalized_codes[0] == normalized_codes[1]:
        return None, 'Choose two different modules.'
    return normalized_codes, None


# Manual TTL cache — avoids re-fetching on every keystroke.
_modules_cache = {'data': None, 'timestamp': 0}
MODULE_CACHE_TTL = 300


_LOCAL_DATA_DIR = os.path.join(_base_dir, 'app', 'static', 'local-data', 'data')


def _load_local_modules() -> list[dict] | None:
    """Load module data from local JSON files as fallback."""
    synopsis_path = os.path.join(_LOCAL_DATA_DIR, 'rp_modules_synopsis.json')
    try:
        with open(synopsis_path, encoding='utf-8') as f:
            synopsis_data = json.load(f)
    except (OSError, KeyError, json.JSONDecodeError):
        return None

    return [{
        'code': m['module_code'],
        'name': m.get('module_name', ''),
        'synopsis': m.get('synopsis', ''),
        'school': m.get('school_name', ''),
        'school_abbr': m.get('school_abbr', ''),
        'url': m.get('url', ''),
    } for m in synopsis_data]


def _load_local_courses() -> list[dict] | None:
    """Load course/diploma data from local JSON file as fallback."""
    courses_path = os.path.join(_LOCAL_DATA_DIR, 'rp_courses.json')
    try:
        with open(courses_path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _load_local_minors() -> list[dict] | None:
    """Load minor programme data from local JSON file as fallback."""
    minors_path = os.path.join(_LOCAL_DATA_DIR, 'rp_minors.json')
    try:
        with open(minors_path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _build_modules_list() -> list | None:
    """Fetch modules from PostgreSQL, falling back to local JSON files."""
    if use_postgres():
        try:
            with pg_connection() as conn, conn.cursor() as cur:
                cur.execute('SELECT module_code, module_name, synopsis, school_name, school_abbr, url FROM rp_modules ORDER BY module_code')
                rows = cur.fetchall()
                if rows:
                    return [{'code': r[0], 'name': r[1], 'synopsis': r[2], 'school': r[3], 'school_abbr': r[4], 'url': r[5]} for r in rows]
        except psycopg2.Error:
            pass

    return _load_local_modules()


def generate_gemini_comparison(modules: list[dict]) -> list[dict]:
    """Generate a transient two-module comparison with the Gemini API."""
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        raise GeminiServiceError('GEMINI_API_KEY is not configured.')

    model = os.environ.get('GEMINI_MODEL', GEMINI_MODEL).strip() or GEMINI_MODEL
    endpoint = (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        f'{model}:generateContent'
    )
    source = [
        {
            'module_code': module.get('code', ''),
            'module_name': module.get('name', ''),
            'school': module.get('school', ''),
            'synopsis': str(module.get('synopsis', ''))[
                :MAX_COMPARISON_SOURCE_LENGTH
            ],
        }
        for module in modules
    ]
    prompt = (
        'Using only this module data, return JSON with a "modules" array in '
        'the same order. Each item needs module_code, an 18-30 word summary, '
        'a 12-22 word suitable_for sentence, and workload with level '
        '(Low, Moderate, High, or Unknown), confidence (Low or Medium), and '
        'a reason under 18 words. Do not invent hours or assessments. '
        f'Data: {json.dumps(source, ensure_ascii=False)}'
    )
    request_body = {
        'contents': [{
            'parts': [{'text': prompt}],
        }],
        'generationConfig': {
            'responseMimeType': 'application/json',
            'maxOutputTokens': 500,
            'temperature': 0.2,
        },
    }

    try:
        response = requests.post(
            endpoint,
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': api_key,
            },
            json=request_body,
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        response_payload = response.json()
        parts = response_payload['candidates'][0]['content']['parts']
        generated = json.loads(parts[0]['text'])
    except (
        requests.RequestException,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        app.logger.warning('Gemini comparison request failed: %s', error)
        raise GeminiServiceError(
            'Gemini could not generate a comparison.'
        ) from error

    rows = generated.get('modules') if isinstance(generated, dict) else None
    if not isinstance(rows, list) or len(rows) != 2:
        raise GeminiServiceError('Gemini returned an invalid comparison.')
    return rows


@app.route('/')
def serve_index():
    """Render the home page with module search functionality."""
    query = request.args.get('q', '')
    return render_template('modules/index.html', query=query)


@app.route('/comparison')
def serve_comparison():
    """Render the module comparison page."""
    return render_template('modules/comparison.html')


@app.route('/bookmarks')
def serve_bookmarks():
    """Render the dedicated bookmarked modules page."""
    return render_template('modules/bookmarks.html')


@app.route('/reviews')
def serve_reviews():
    """Render the review dashboard page."""
    return render_template('modules/reviews.html')


@app.route('/api/modules', methods=['GET'])
def get_modules():
    """Return all modules with generated comparison fields.

    Results are cached for MODULE_CACHE_TTL seconds to avoid
    re-running regex matching on every request.
    """
    now = time.time()
    if _modules_cache['data'] is not None and (now - _modules_cache['timestamp']) < MODULE_CACHE_TTL:
        return jsonify(_modules_cache['data']), 200

    modules = _build_modules_list()
    if modules is None:
        return jsonify({'error': 'Module data is not available.'}), 503

    _modules_cache['data'] = modules
    _modules_cache['timestamp'] = now
    return jsonify(modules), 200


_courses_cache = {'data': None, 'timestamp': 0}
COURSES_CACHE_TTL = 300


@app.route('/api/courses', methods=['GET'])
def get_courses():
    """Return all courses (diplomas) from PostgreSQL rp_courses table."""
    now = time.time()
    if _courses_cache['data'] is not None and (now - _courses_cache['timestamp']) < COURSES_CACHE_TTL:
        return jsonify(_courses_cache['data']), 200

    courses = None

    if use_postgres():
        try:
            with pg_connection() as conn, conn.cursor() as cur:
                cur.execute('SELECT course_code, course_name, school_name, school_abbr, url, general_modules, major_modules, discipline_modules, elective_modules, industry_modules, major_groups FROM rp_courses')
                rows = cur.fetchall()
                if rows:
                    courses = [{
                        'course_code': r[0], 'course_name': r[1], 'school_name': r[2],
                        'school_abbr': r[3], 'url': r[4],
                        'general_modules': r[5] if isinstance(r[5], list) else json.loads(r[5]) if r[5] else [],
                        'major_modules': r[6] if isinstance(r[6], list) else json.loads(r[6]) if r[6] else [],
                        'discipline_modules': r[7] if isinstance(r[7], list) else json.loads(r[7]) if r[7] else [],
                        'elective_modules': r[8] if isinstance(r[8], list) else json.loads(r[8]) if r[8] else [],
                        'industry_modules': r[9] if isinstance(r[9], list) else json.loads(r[9]) if r[9] else [],
                        'major_groups': r[10] if isinstance(r[10], (list, dict)) else json.loads(r[10]) if r[10] else [],
                    } for r in rows]
        except (psycopg2.Error, json.JSONDecodeError):
            pass

    if courses is None:
        courses = _load_local_courses()

    if courses is None:
        return jsonify({'error': 'No course data available.'}), 503

    _courses_cache['data'] = courses
    _courses_cache['timestamp'] = now
    return jsonify(courses), 200


_minors_cache = {'data': None, 'timestamp': 0}
MINORS_CACHE_TTL = 300


@app.route('/api/minors', methods=['GET'])
def get_minors():
    """Return all minor programmes from PostgreSQL rp_minors table."""
    now = time.time()
    if _minors_cache['data'] is not None and (now - _minors_cache['timestamp']) < MINORS_CACHE_TTL:
        return jsonify(_minors_cache['data']), 200

    minors = None

    if use_postgres():
        try:
            with pg_connection() as conn, conn.cursor() as cur:
                cur.execute('SELECT minor_name, minor_type, url, modules, eligibility FROM rp_minors')
                rows = cur.fetchall()
                if rows:
                    minors = [{
                        'minor_name': r[0], 'minor_type': r[1], 'url': r[2],
                        'modules': r[3] if isinstance(r[3], list) else json.loads(r[3]) if r[3] else [],
                        'eligibility': r[4],
                    } for r in rows]
        except (psycopg2.Error, json.JSONDecodeError):
            pass

    if minors is None:
        minors = _load_local_minors()

    if minors is None:
        return jsonify({'error': 'No minor data available.'}), 503

    _minors_cache['data'] = minors
    _minors_cache['timestamp'] = now
    return jsonify(minors), 200


@app.route('/api/reviews', methods=['GET'])
def list_reviews():
    """Return all reviews ordered by creation date for the dashboard."""
    reviews = ReviewRepository.list_all(request_identity())
    return jsonify(reviews), 200


@app.route('/api/reviews', methods=['POST'])
@limiter.limit("20/hour")
def add_review():
    """Create a new review for a module."""
    payload, error = validate_review_payload(
        request.get_json(silent=True),
        require_module_code=True,
    )
    if error:
        return jsonify({'error': error}), 400

    review, error_response = ReviewRepository.create(
        payload,
        request_identity(create_guest=True),
    )
    if error_response:
        return error_response
    return jsonify(review), 201


@app.route('/api/reviews/<module_code>', methods=['GET'])
def get_reviews(module_code):
    """Return all reviews for a specific module code."""
    reviews = ReviewRepository.list_by_module(
        module_code,
        request_identity(),
    )
    return jsonify(reviews), 200


@app.route('/api/reviews/<int:review_id>', methods=['PUT'])
@limiter.limit("10/hour")
def update_review(review_id):
    """Update an existing review by ID."""
    payload, error = validate_review_payload(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400

    review, error_response = ReviewRepository.update(
        review_id,
        payload,
        request_identity(create_guest=True),
    )
    if error_response:
        return error_response
    return jsonify(review), 200


@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@limiter.limit("10/hour")
def delete_review(review_id):
    """Delete a review by ID."""
    error_response = ReviewRepository.delete(
        review_id,
        request_identity(create_guest=True),
    )
    if error_response:
        return error_response
    return '', 204


@app.route('/api/reviews/<int:review_id>/vote', methods=['GET'])
def get_review_votes(review_id):
    """Return vote score and user's vote for a review."""
    votes = VoteRepository.get_votes(review_id, request_identity())
    return jsonify(votes), 200


@app.route('/api/reviews/<int:review_id>/vote', methods=['POST'])
@limiter.limit("30/hour")
def vote_review(review_id):
    """Add or update a vote on a review."""
    payload = request.get_json(silent=True)
    if not payload or 'vote_type' not in payload:
        return jsonify({'error': 'vote_type is required (1 or -1).'}), 400

    vote_type = payload['vote_type']
    if vote_type not in (1, -1):
        return jsonify({'error': 'vote_type must be 1 or -1.'}), 400

    result, error_response = VoteRepository.vote(
        review_id,
        vote_type,
        request_identity(create_guest=True),
    )
    if error_response:
        return error_response
    return jsonify(result), 200


@app.route('/api/reviews/<int:review_id>/vote', methods=['DELETE'])
@limiter.limit("30/hour")
def remove_review_vote(review_id):
    """Remove a user's vote from a review."""
    VoteRepository.remove(
        review_id,
        request_identity(create_guest=True),
    )
    return '', 204


@app.route('/api/reviews/votes', methods=['POST'])
def get_bulk_votes():
    """Return vote scores for multiple reviews at once."""
    payload = request.get_json(silent=True)
    if not payload or 'review_ids' not in payload:
        return jsonify({'error': 'review_ids array is required.'}), 400

    review_ids = payload['review_ids']
    if not isinstance(review_ids, list):
        return jsonify({'error': 'review_ids must be an array.'}), 400

    votes = VoteRepository.get_votes_bulk(review_ids, request_identity())
    return jsonify(votes), 200


def _authenticated_identity():
    """Return the current account identity or a standard 401 response."""
    identity = request_identity()
    if not identity or identity['kind'] != 'account':
        return None, (jsonify({'error': 'Login required.'}), 401)
    return identity, None


@app.route('/api/bookmarks', methods=['GET'])
def get_bookmarks():
    """Return cross-device bookmarks for the current account."""
    identity, error = _authenticated_identity()
    if error:
        return error
    return jsonify({
        'module_codes': BookmarkRepository.list_for_user(identity['user_id'])
    }), 200


@app.route('/api/bookmarks/<module_code>', methods=['PUT'])
def add_bookmark(module_code):
    """Add one cross-device account bookmark."""
    identity, error = _authenticated_identity()
    if error:
        return error
    code, repository_error = BookmarkRepository.add(
        identity['user_id'],
        module_code,
    )
    if repository_error:
        return repository_error
    return jsonify({'module_code': code}), 200


@app.route('/api/bookmarks/<module_code>', methods=['DELETE'])
def delete_bookmark(module_code):
    """Delete one cross-device account bookmark."""
    identity, error = _authenticated_identity()
    if error:
        return error
    BookmarkRepository.remove(identity['user_id'], module_code)
    return '', 204


@app.route('/api/bookmarks', methods=['DELETE'])
def clear_bookmarks():
    """Delete every cross-device account bookmark."""
    identity, error = _authenticated_identity()
    if error:
        return error
    BookmarkRepository.remove(identity['user_id'])
    return '', 204


@app.route('/api/ownership/pending', methods=['GET'])
def get_pending_ownership():
    """Describe claimable signed-guest activity for the logged-in account."""
    _identity, error = _authenticated_identity()
    if error:
        return error
    counts = OwnershipRepository.pending_counts(current_guest_hash())
    return jsonify(counts), 200


@app.route('/api/ownership/claim', methods=['POST'])
def claim_guest_ownership():
    """Explicitly transfer this browser's guest activity to its account."""
    identity, error = _authenticated_identity()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    bookmark_codes = payload.get('bookmark_codes', [])
    if not isinstance(bookmark_codes, list):
        return jsonify({'error': 'bookmark_codes must be an array.'}), 400
    result = OwnershipRepository.claim(
        identity,
        current_guest_hash(),
        bookmark_codes,
    )
    rotate_guest_cookie()
    return jsonify(result), 200


@app.route('/api/ratings', methods=['GET'])
def get_rating_summaries():
    """Return average, review count, and distribution for each module."""
    summaries = ReviewRepository.rating_summaries()
    return jsonify(summaries), 200


@app.route('/api/comparison/generate', methods=['POST'])
@limiter.limit("15/hour")
def generate_comparison():
    """Generate a transient Gemini comparison for two catalogue modules."""
    module_codes, error = validate_comparison_payload(
        request.get_json(silent=True)
    )
    if error:
        return jsonify({'error': error}), 400

    catalogue = _modules_cache['data'] or _build_modules_list()
    if catalogue is None:
        return jsonify({'error': 'Module data is not available.'}), 503

    catalogue_by_code = {
        str(module.get('code', '')).upper(): module
        for module in catalogue
    }
    missing_codes = [
        code for code in module_codes if code not in catalogue_by_code
    ]
    if missing_codes:
        return jsonify({
            'error': f"Unknown module code: {', '.join(missing_codes)}."
        }), 404

    selected_modules = [catalogue_by_code[code] for code in module_codes]
    if not os.environ.get('GEMINI_API_KEY', '').strip():
        return jsonify({
            'error': 'Dynamic comparison is not configured.'
        }), 503
    try:
        generated_modules = generate_gemini_comparison(selected_modules)
    except GeminiServiceError:
        return jsonify({
            'error': 'Dynamic comparison is temporarily unavailable.'
        }), 502

    return jsonify({
        'provider': 'Gemini',
        'model': os.environ.get('GEMINI_MODEL', GEMINI_MODEL),
        'modules': generated_modules,
    }), 200


@app.route('/api/career-paths', methods=['GET'])
def get_career_paths():
    """Return career paths — delegates to _load_career_paths()."""
    return jsonify(_load_career_paths()), 200

_CAREER_KEYWORD_STOPWORDS = frozenset({
    'what', 'where', 'when', 'which', 'why', 'this', 'that', 'with', 'want',
    'like', 'tell', 'show', 'how', 'can', 'for', 'the', 'and', 'are', 'you',
    'about', 'some', 'have', 'from', 'your', 'know', 'just', 'also', 'more',
    'any', 'all', 'not', 'get', 'use', 'could', 'would', 'does', 'there',
    'their', 'they', 'them', 'been', 'were', 'was', 'has', 'had', 'but',
    'its', 'into', 'than', 'then', 'very', 'will', 'got', 'say'
})


def _get_active_module_codes() -> frozenset:
    """Return frozenset of module codes linked to active courses/diplomas."""
    courses = None

    if use_postgres():
        try:
            with pg_connection() as conn, conn.cursor() as cur:
                cur.execute('SELECT general_modules, major_modules, discipline_modules, elective_modules, industry_modules FROM rp_courses')
                rows = cur.fetchall()
                if rows:
                    courses = []
                    for r in rows:
                        row = {}
                        for i, field in enumerate(('general_modules', 'major_modules', 'discipline_modules', 'elective_modules', 'industry_modules')):
                            val = r[i]
                            row[field] = val if isinstance(val, list) else json.loads(val) if val else []
                        courses.append(row)
        except (psycopg2.Error, json.JSONDecodeError):
            pass

    if courses is None:
        courses = _load_local_courses()
    if not courses:
        return frozenset()

    codes = set()
    for c in courses:
        for field in ('general_modules', 'major_modules', 'discipline_modules', 'elective_modules', 'industry_modules'):
            for m in (c.get(field) or []):
                code = m.get('code', '') if isinstance(m, dict) else str(m)
                if code:
                    codes.add(code.upper())
    return frozenset(codes)


def _gobot_find_diplomas(module_codes, courses):
    """Find diploma programmes that contain the given module codes.
    Returns list of (course, match_count) sorted by relevance."""
    if not courses:
        courses = _load_local_courses()
    if not courses or not module_codes:
        return []

    code_set = {c.upper() for c in module_codes}
    results = []
    for course in courses:
        course_modules = set()
        for field in ('general_modules', 'major_modules', 'discipline_modules', 'elective_modules', 'industry_modules'):
            for m in (course.get(field) or []):
                code = m.get('code', '') if isinstance(m, dict) else str(m)
                if code:
                    course_modules.add(code.upper())
        overlap = code_set & course_modules
        if overlap:
            results.append((course, len(overlap)))
    results.sort(key=lambda x: -x[1])
    return results[:5]


def _gobot_find_candidates(user_msg, modules, careers):
    """Score modules against user message using career keywords or direct word matching.
    Returns (candidates_list, matched_career_or_None)."""
    msg_lower = user_msg.lower()

    matched_career = None
    for c in careers:
        if c['label'].lower() in msg_lower:
            matched_career = c
            break
        for kw in c.get('keywords', []):
            if kw.lower() in msg_lower:
                matched_career = c
                break
        if matched_career:
            break

    if matched_career:
        keywords = list(matched_career['keywords'])
    else:
        tokens = re.findall(r'[a-z]{4,}', msg_lower)
        keywords = [t for t in tokens if t not in _CAREER_KEYWORD_STOPWORDS]

    if not keywords:
        return [], None

    scored = []
    for m in modules:
        haystack = f" {m.get('name', '')} {m.get('synopsis', '')} ".lower()
        s = sum(1 for kw in keywords if kw.lower() in haystack)
        if s >= 2:
            scored.append((s, m))
    scored.sort(key=lambda x: (-x[0], x[1].get('code', '')))
    return [m for _, m in scored[:15]], matched_career


def _gobot_gemini_recommend(user_msg, history, candidates, careers):
    """Use Gemini to generate a recommendation response from candidate modules.
    Returns dict with reply / links / suggestions or None."""
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key or not candidates:
        return None

    model = os.environ.get('GEMINI_MODEL', GEMINI_MODEL).strip() or GEMINI_MODEL
    endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

    module_lines = []
    for m in candidates[:10]:
        synopsis = (m.get('synopsis') or '')[:150]
        module_lines.append(f"{m['code']}: {m['name']} — {synopsis}")
    module_text = '\n'.join(module_lines)

    career_labels = ', '.join(c['label'] for c in careers)

    history_text = ''
    if history:
        lines = []
        for m in history[-4:]:
            role = 'User' if m.get('role') == 'user' else 'GoBot'
            lines.append(f"{role}: {m.get('text', '')}")
        history_text = '\n'.join(lines)

    prompt = f"""You are GoBot, a module advisor for Republic Polytechnic. Your main job is recommending modules based on career goals and interests.

Available career paths: {career_labels}

Matching active modules from current diploma programmes:
{module_text}

Analyze the user's interests. Pick 2-4 modules from this list that best fit their goals. Explain why each one is relevant.

Rules:
- ONLY recommend modules from the list above. Never invent codes.
- Be concise and encouraging. No markdown.
- Suggest 1-2 follow-up questions the user might ask next.

Respond in JSON format:
{{"reply": "your response here", "recommendations": [{{"code": "C270", "name": "Mobile App Development"}}], "suggestions": ["Compare C270 and C350", "Show me Cybersecurity careers"]}}{f'''

Recent conversation:
{history_text}''' if history_text else ''}

User: {user_msg}
Assistant:"""

    request_body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'responseMimeType': 'application/json',
            'maxOutputTokens': 800,
            'temperature': 0.4,
        },
    }

    try:
        response = requests.post(
            endpoint,
            headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key},
            json=request_body,
            timeout=GEMINI_TIMEOUT_SECONDS + 5,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload['candidates'][0]['content']['parts'][0]['text']
        result = json.loads(text)

        valid_codes = {m['code'].lower() for m in candidates}
        result['recommendations'] = [
            r for r in result.get('recommendations', [])
            if r.get('code', '').lower() in valid_codes
        ]

        if not result.get('reply') or not result.get('recommendations'):
            return None

        rec_codes = [r['code'] for r in result['recommendations']]
        courses = _load_local_courses()
        diplomas = _gobot_find_diplomas(rec_codes, courses)

        links = [{"text": f"{r['code']} — {r.get('name', '')}", "url": f"/?q={r['code']}"} for r in result['recommendations']]
        for course, count in diplomas[:2]:
            name = course.get('course_name', '')
            if name:
                links.append({"text": f"🎓 {name}", "url": course.get('url', '/')})

        return {
            "reply": result['reply'],
            "links": links,
            "suggestions": result.get('suggestions', []),
        }
    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError):
        return None


@app.route('/api/gobot', methods=['POST'])
@limiter.limit("30/hour")
def gobot_chat():
    """GoBot — AI-powered module recommendation advisor."""
    data = request.json or {}
    user_msg = (data.get('message', '') or '').strip()[:500]
    history = (data.get('history', []) or [])[-6:]
    for m in history:
        if 'text' in m:
            m['text'] = m['text'][:500]
    if not user_msg:
        return jsonify({"reply": "Ask me about careers and modules!", "links": [], "suggestions": []})

    modules = _build_modules_list() or []
    active_codes = _get_active_module_codes()
    if active_codes:
        modules = [m for m in modules if m['code'].upper() in active_codes]
    careers = _load_career_paths()
    module_map = {m['code'].lower(): m for m in modules}
    msg_lower = user_msg.lower().strip()

    # --- Fast paths (no Gemini) ---

    for t in user_msg.split():
        clean = re.sub(r'[^a-z0-9]', '', t.lower())
        if clean in module_map:
            m = module_map[clean]
            return jsonify({
                "reply": f"{m['code']} — {m['name']}\n{m.get('synopsis', '')[:200]}",
                "links": [
                    {"text": "View details", "url": f"/?q={m['code']}"},
                    {"text": "Compare", "url": f"/comparison?id={m['code']}"},
                ],
                "suggestions": [f"Reviews for {m['code']}", f"Compare {m['code']}"],
                })

    if re.match(r'^(hi|hello|hey|howdy|yo|sup)\b', msg_lower):
        return jsonify({
            "reply": "Hi! Tell me what career or interests you're exploring, and I'll recommend modules for you!",
            "links": [],
            "suggestions": ["I like designing websites", "I want to build software", "Tell me about careers"],
        })

    m = re.search(r'(?:reviews?|rating|feedback)\s+(?:for|of|about|on)?\s*([a-z]\d{3})', msg_lower)
    if m:
        code = m.group(1).lower()
        if code in module_map:
            mod = module_map[code]
            reviews = ReviewRepository.list_by_module(mod['code'])
            ratings = ReviewRepository.rating_summaries().get(mod['code'])
            links = [{"text": "Write a review →", "url": "/reviews"}]
            if reviews:
                avg = ratings.get('average_rating', 0) if ratings else 0
                rc = ratings.get('review_count', len(reviews)) if ratings else len(reviews)
                for r in reversed(reviews[:3]):
                    stars = '⭐' * r['rating']
                    comment = r['comment'][:80] + ('…' if len(r['comment']) > 80 else '')
                    links.insert(0, {"text": f"{stars} \"{comment}\"", "url": f"/?q={mod['code']}"})
                stars = '⭐' * round(avg) if avg else ''
                reply = f"{mod['code']} — {mod['name']}\n{stars} {avg:.1f}/5 ({rc} reviews)\n\nRecent reviews:"
            else:
                reply = f"{mod['code']} has no reviews yet. Be the first!"
            return jsonify({"reply": reply, "links": links, "suggestions": []})
        return jsonify({"reply": f"Couldn't find module '{code}'.", "links": [], "suggestions": []})

    if re.search(r'(where|navigate|how to|how do i|guide|help|what can|what does)', msg_lower):
        return jsonify({
            "reply": "Here's how to get around:",
            "links": [
                {"text": "Search Modules", "url": "/"},
                {"text": "Compare Modules", "url": "/comparison"},
                {"text": "Reviews Dashboard", "url": "/reviews"},
            ],
            "suggestions": ["What modules for Data Analyst?", "Tell me about C270"],
        })

    if 'modulego' in msg_lower or 'module go' in msg_lower:
        return jsonify({
            "reply": "ModuleGo helps Republic Polytechnic students discover and compare modules. Tell me your career goals and I'll recommend the right modules for you!",
            "links": [],
            "suggestions": ["I like programming", "What modules for Data Analyst?"],
        })

    # --- Main: AI-powered recommendation ---
    candidates, matched_career = _gobot_find_candidates(user_msg, modules, careers)

    result = _gobot_gemini_recommend(user_msg, history, candidates, careers)
    if result:
        return jsonify(result)

    # Fallback: use keyword-matched candidates directly
    if candidates:
        top = candidates[:5]
        tag = matched_career['label'] if matched_career else 'your interests'
        lines = [f"Based on {tag}, here are relevant modules:"]
        for mod in top:
            lines.append(f"• {mod['code']} — {mod['name']}")
        rec_codes = [mod['code'] for mod in top]
        courses = _load_local_courses()
        diplomas = _gobot_find_diplomas(rec_codes, courses)
        links = [{"text": f"{mod['code']} — {mod['name']}", "url": f"/?q={mod['code']}"} for mod in top]
        for course, count in diplomas[:2]:
            name = course.get('course_name', '')
            if name:
                links.append({"text": f"🎓 {name}", "url": course.get('url', '/')})
        return jsonify({
            "reply": '\n'.join(lines),
            "links": links,
            "suggestions": ["Compare these modules", "Show me more options", "Try another career"],
        })

    return jsonify({
        "reply": "Tell me about your interests or career goals, and I'll recommend modules for you!",
        "links": [],
        "suggestions": ["I want to be a Data Analyst", "I like programming", "Show me careers"],
    })


def _load_career_paths() -> list:
    """Load career paths from DB (SQLite/PostgreSQL), with file + hardcoded fallback."""
    if use_sqlite_reviews():
        try:
            with database_connection() as conn:
                rows = conn.execute(
                    f'SELECT CAREER_ID, LABEL, KEYWORDS FROM {_CAREER_PATHS_TABLE} ORDER BY ID'
                ).fetchall()
                if rows:
                    return [{'id': r[0], 'label': r[1], 'keywords': json.loads(r[2])} for r in rows]
        except (sqlite3.Error, json.JSONDecodeError):
            pass
        paths = _load_career_paths_from_file()
        if paths:
            return paths
        return _CAREER_FALLBACK

    if use_postgres():
        try:
            with pg_connection() as conn, conn.cursor() as cur:
                cur.execute(f'SELECT CAREER_ID, LABEL, KEYWORDS FROM {_CAREER_PATHS_TABLE} ORDER BY ID')
                rows = cur.fetchall()
                if rows:
                    return [{'id': r[0], 'label': r[1], 'keywords': r[2] if isinstance(r[2], list) else json.loads(r[2]) if r[2] else []} for r in rows]
        except (psycopg2.Error, json.JSONDecodeError):
            pass
        paths = _load_career_paths_from_file()
        if paths:
            return paths
        return _CAREER_FALLBACK

    paths = _load_career_paths_from_file()
    if paths:
        return paths
    return _CAREER_FALLBACK


_CAREER_FALLBACK = [
    {"id": "data-analyst", "label": "Data Analyst", "keywords": ["data","analytics","python","sql","visualization","power bi","statistics","excel","tableau"]},
    {"id": "data-scientist", "label": "Data Scientist", "keywords": ["machine learning","deep learning","python","statistics","ai","neural network","predictive","nlp"]},
    {"id": "cybersecurity", "label": "Cybersecurity", "keywords": ["security","cyber","network","ethical hacking","forensic","encryption","firewall","penetration"]},
    {"id": "software-engineer", "label": "Software Engineer", "keywords": ["programming","software","web","app","java","agile","javascript","python","testing","api"]},
    {"id": "ui-ux", "label": "UI/UX Designer", "keywords": ["design","ui","ux","figma","user experience","wireframe","prototype","accessibility","interaction"]},
    {"id": "ai-ml-engineer", "label": "AI/ML Engineer", "keywords": ["artificial intelligence","machine learning","deep learning","neural","nlp","computer vision","tensorflow","pytorch"]},
    {"id": "cloud-devops", "label": "Cloud / DevOps Engineer", "keywords": ["cloud","devops","docker","kubernetes","ci/cd","aws","azure","infrastructure","automation","deployment"]},
    {"id": "mobile-developer", "label": "Mobile App Developer", "keywords": ["mobile","android","ios","flutter","react native","swift","kotlin","app development"]},
    {"id": "game-developer", "label": "Game Developer", "keywords": ["game","unity","unreal","3d","animation","graphics","rendering","physics"]},
    {"id": "business-analyst", "label": "Business Analyst", "keywords": ["business","requirements","process","stakeholder","documentation","uml","agile","project management"]},
    {"id": "network-engineer", "label": "Network Engineer", "keywords": ["network","routing","switching","tcp/ip","cisco","infrastructure","protocol","lan","wan"]},
    {"id": "digital-marketer", "label": "Digital Marketing", "keywords": ["marketing","social media","seo","analytics","content","e-commerce","campaign","brand"]},
    {"id": "fintech-developer", "label": "Fintech Developer", "keywords": ["fintech","blockchain","payment","banking","cryptocurrency","smart contract","financial"]},
    {"id": "iot-engineer", "label": "IoT / Embedded Systems Engineer", "keywords": ["iot","embedded","sensor","microcontroller","arduino","raspberry pi","firmware","hardware"]},
]


# ---------------------------------------------------------------------------
# CSRF exemptions for read-only or stateless API endpoints
# ---------------------------------------------------------------------------

csrf.exempt(get_modules)
csrf.exempt(get_courses)
csrf.exempt(list_reviews)
csrf.exempt(get_reviews)
csrf.exempt(get_rating_summaries)
csrf.exempt(generate_comparison)
csrf.exempt(get_career_paths)
csrf.exempt(gobot_chat)
csrf.exempt(get_review_votes)
csrf.exempt(get_bulk_votes)


if __name__ == '__main__':
    print("ModuleGo Backend Server running on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

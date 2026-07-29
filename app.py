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
from uuid import uuid4

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from postgrest.exceptions import APIError
from supabase import create_client

load_dotenv()

app = Flask(__name__,
            static_folder='app/static',
            template_folder='app/templates')

csrf = CSRFProtect()


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
MAX_COMMENT_LENGTH = 500
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.1-flash-lite')
GEMINI_TIMEOUT_SECONDS = 25
MAX_COMPARISON_SOURCE_LENGTH = 4000


class GeminiServiceError(RuntimeError):
    """Raised when Gemini cannot return a valid comparison."""


def _owner_token_from_request() -> str | None:
    """Extract and strip the owner token from request headers."""
    return request.headers.get('X-Owner-Token', '').strip() or None


def generate_owner_token() -> str:
    """Generate a random 32-char hex token for anonymous review ownership."""
    return uuid4().hex

supabase_url = os.environ.get('SUPABASE_URL')
supabase_secret_key = os.environ.get('SUPABASE_SECRET_KEY')
supabase = None

if supabase_url and supabase_secret_key:
    if not supabase_url.startswith(('https://', 'http://')):
        raise RuntimeError('SUPABASE_URL must be a complete HTTP(S) URL.')
    if supabase_secret_key.startswith('sb_publishable_'):
        raise RuntimeError(
            'SUPABASE_SECRET_KEY must use the backend-only sb_secret_ key, not a '
            'publishable browser key.'
        )
    supabase = create_client(supabase_url, supabase_secret_key)
db_name = os.environ.get('DATABASE_PATH', os.path.join(_base_dir, 'modulego.db'))
database_url = os.environ.get('DATABASE_URL')

csrf.init_app(app)
limiter.init_app(app)


def _get_commit_hash() -> str | None:
    """Return the short git commit hash, or None if unavailable."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, cwd=_base_dir, timeout=5, check=False
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    # Vercel deployments lack a .git directory, so fall back to env injection.
    vercel_sha = os.environ.get('VERCEL_GIT_COMMIT_SHA')
    return vercel_sha[:7] if vercel_sha else None


@app.context_processor
def inject_globals():
    """Inject global template variables into all Jinja templates."""
    return {
        'current_year': datetime.now(timezone.utc).year,
        'commit_hash': _get_commit_hash(),
    }


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

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
    """Return True when SQLite should be used (tests or Supabase unavailable)."""
    if app.config.get('TESTING'):
        return True
    return supabase is None and not database_url


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


def review_to_dict(row: sqlite3.Row) -> dict:
    """Convert a database row to a review dictionary."""
    return {
        'id': row['ID'],
        'module_code': row['MODULE_CODE'],
        'rating': row['RATING'],
        'comment': row['COMMENT'],
        'created_at': row['CREATED_AT'],
        'updated_at': row['UPDATED_AT'],
        'owner_token': row['OWNER_TOKEN'],
    }


def select_review(conn: sqlite3.Connection, review_id: int) -> sqlite3.Row:
    """Fetch a single review by ID from the database."""
    return conn.execute(
        '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT, UPDATED_AT, OWNER_TOKEN
           FROM REVIEWS WHERE ID = ?''',
        (review_id,),
    ).fetchone()


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
                OWNER_TOKEN TEXT)'''
        )
        columns = {
            row['name']
            for row in conn.execute('PRAGMA table_info(REVIEWS)').fetchall()
        }
        if 'UPDATED_AT' not in columns:
            conn.execute('ALTER TABLE REVIEWS ADD COLUMN UPDATED_AT DATETIME')
        if 'OWNER_TOKEN' not in columns:
            conn.execute('ALTER TABLE REVIEWS ADD COLUMN OWNER_TOKEN TEXT')
        conn.execute(
            'CREATE INDEX IF NOT EXISTS IDX_REVIEWS_MODULE_CODE '
            'ON REVIEWS (MODULE_CODE)'
        )
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS REVIEW_VOTES
               (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                REVIEW_ID INTEGER NOT NULL,
                OWNER_TOKEN TEXT NOT NULL,
                VOTE_TYPE INTEGER NOT NULL CHECK (VOTE_TYPE IN (1, -1)),
                CREATED_AT DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (REVIEW_ID) REFERENCES REVIEWS(ID) ON DELETE CASCADE,
                UNIQUE(REVIEW_ID, OWNER_TOKEN))'''
        )
        conn.execute(
            'CREATE INDEX IF NOT EXISTS IDX_REVIEW_VOTES_REVIEW_ID '
            'ON REVIEW_VOTES (REVIEW_ID)'
        )
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS CAREER_PATHS
               (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                CAREER_ID TEXT NOT NULL UNIQUE,
                LABEL TEXT NOT NULL,
                KEYWORDS TEXT NOT NULL DEFAULT '[]')'''
        )
    _seed_career_paths()


def _load_career_paths_from_file() -> list | None:
    """Read career paths from local JSON file. Returns None if all fail."""
    for name in ('rp_career_paths.json',):
        for folder in ('local-data',):
            p = os.path.join(_base_dir, 'app', 'static', folder, 'data', name)
            try:
                with open(p, encoding='utf-8') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
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
                OWNER_TOKEN TEXT)'''
        )
        cur.execute(
            'CREATE INDEX IF NOT EXISTS IDX_REVIEWS_MODULE_CODE ON REVIEWS (MODULE_CODE)'
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS REVIEW_VOTES
               (ID SERIAL PRIMARY KEY,
                REVIEW_ID INTEGER NOT NULL,
                OWNER_TOKEN TEXT NOT NULL,
                VOTE_TYPE INTEGER NOT NULL CHECK (VOTE_TYPE IN (1, -1)),
                CREATED_AT TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (REVIEW_ID) REFERENCES REVIEWS(ID) ON DELETE CASCADE,
                UNIQUE(REVIEW_ID, OWNER_TOKEN))'''
        )
        cur.execute(
            'CREATE INDEX IF NOT EXISTS IDX_REVIEW_VOTES_REVIEW_ID ON REVIEW_VOTES (REVIEW_ID)'
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS CAREER_PATHS
               (ID SERIAL PRIMARY KEY,
                CAREER_ID TEXT NOT NULL UNIQUE,
                LABEL TEXT NOT NULL,
                KEYWORDS TEXT NOT NULL DEFAULT '[]')'''
        )
    _seed_pg_career_paths()


def _seed_pg_career_paths() -> None:
    """Seed career paths from local JSON into PostgreSQL if table is empty."""
    with pg_connection() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM CAREER_PATHS')
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
                    'INSERT INTO CAREER_PATHS (CAREER_ID, LABEL, KEYWORDS) VALUES (%s, %s, %s)',
                    (p['id'], p['label'], json.dumps(p.get('keywords', [])))
                )
            except psycopg2.Error:
                continue


if use_sqlite_reviews():
    init_db()
elif use_postgres():
    init_pg_db()


# ---------------------------------------------------------------------------
# Review repository - encapsulates dual-database branching
# ---------------------------------------------------------------------------

class ReviewRepository:
    """Handles review persistence for SQLite, PostgreSQL, and Supabase."""

    @staticmethod
    def list_all() -> list:
        """Return all reviews ordered by creation date descending."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                rows = conn.execute(
                    '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT, UPDATED_AT, OWNER_TOKEN
                       FROM REVIEWS ORDER BY CREATED_AT DESC, ID DESC'''
                ).fetchall()
            return [review_to_dict(row) for row in rows]

        if use_postgres():
            with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT, UPDATED_AT, OWNER_TOKEN
                       FROM REVIEWS ORDER BY CREATED_AT DESC, ID DESC'''
                )
                rows = cur.fetchall()
            return [dict(row) for row in rows]

        result = (
            supabase.table('reviews')
            .select('id,module_code,rating,comment,created_at,updated_at,owner_token')
            .order('created_at', desc=True)
            .execute()
        )
        return result.data

    @staticmethod
    def list_by_module(module_code: str) -> list:
        """Return all reviews for a specific module code."""
        normalized = module_code.strip().upper()
        if use_sqlite_reviews():
            with database_connection() as conn:
                rows = conn.execute(
                    '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT, UPDATED_AT, OWNER_TOKEN
                       FROM REVIEWS WHERE MODULE_CODE = ?
                       ORDER BY CREATED_AT DESC, ID DESC''',
                    (normalized,),
                ).fetchall()
            return [review_to_dict(row) for row in rows]

        if use_postgres():
            with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT, UPDATED_AT, OWNER_TOKEN
                       FROM REVIEWS WHERE MODULE_CODE = %s
                       ORDER BY CREATED_AT DESC, ID DESC''',
                    (normalized,),
                )
                rows = cur.fetchall()
            return [dict(row) for row in rows]

        result = (
            supabase.table('reviews')
            .select('id,module_code,rating,comment,created_at,updated_at,owner_token')
            .eq('module_code', normalized)
            .order('created_at', desc=True)
            .execute()
        )
        return result.data

    @staticmethod
    def create(payload: dict) -> tuple:
        """Create a new review. Returns (review_dict, error_response)."""
        owner_token = payload.pop('owner_token', None)
        if not owner_token:
            owner_token = generate_owner_token()

        if use_sqlite_reviews():
            with database_connection() as conn:
                cursor = conn.execute(
                    '''INSERT INTO REVIEWS (MODULE_CODE, RATING, COMMENT, OWNER_TOKEN)
                       VALUES (?, ?, ?, ?)''',
                    (payload['module_code'], payload['rating'], payload['comment'], owner_token),
                )
                row = select_review(conn, cursor.lastrowid)
            return review_to_dict(row), None

        if use_postgres():
            with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    '''INSERT INTO REVIEWS (MODULE_CODE, RATING, COMMENT, OWNER_TOKEN)
                       VALUES (%s, %s, %s, %s)
                       RETURNING ID, MODULE_CODE, RATING, COMMENT, CREATED_AT, UPDATED_AT, OWNER_TOKEN''',
                    (payload['module_code'], payload['rating'], payload['comment'], owner_token),
                )
                row = cur.fetchone()
            return dict(row), None

        try:
            result = supabase.table('reviews').insert({**payload, 'owner_token': owner_token}).execute()
        except APIError as error:
            if error.code == '23503':
                return None, (jsonify({'error': 'Module code does not exist.'}), 400)
            raise
        return result.data[0], None

    @staticmethod
    def update(review_id: int, payload: dict, owner_token: str | None = None) -> tuple:
        """Update an existing review. Returns (review_dict, error_response)."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                existing = conn.execute(
                    'SELECT OWNER_TOKEN FROM REVIEWS WHERE ID = ?', (review_id,)
                ).fetchone()
                if not existing:
                    return None, (jsonify({'error': 'Review not found.'}), 404)
                if owner_token and existing['OWNER_TOKEN'] and existing['OWNER_TOKEN'] != owner_token:
                    return None, (jsonify({'error': 'Forbidden: you do not own this review.'}), 403)
                conn.execute(
                    '''UPDATE REVIEWS
                       SET RATING = ?, COMMENT = ?, UPDATED_AT = CURRENT_TIMESTAMP
                       WHERE ID = ?''',
                    (payload['rating'], payload['comment'], review_id),
                )
                row = select_review(conn, review_id)
            return review_to_dict(row), None

        if use_postgres():
            with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    'SELECT OWNER_TOKEN FROM REVIEWS WHERE ID = %s', (review_id,)
                )
                existing = cur.fetchone()
                if not existing:
                    return None, (jsonify({'error': 'Review not found.'}), 404)
                if owner_token and existing['OWNER_TOKEN'] and existing['OWNER_TOKEN'] != owner_token:
                    return None, (jsonify({'error': 'Forbidden: you do not own this review.'}), 403)
                cur.execute(
                    '''UPDATE REVIEWS
                       SET RATING = %s, COMMENT = %s, UPDATED_AT = CURRENT_TIMESTAMP
                       WHERE ID = %s''',
                    (payload['rating'], payload['comment'], review_id),
                )
                cur.execute(
                    '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT, UPDATED_AT, OWNER_TOKEN
                       FROM REVIEWS WHERE ID = %s''',
                    (review_id,),
                )
                row = cur.fetchone()
            return dict(row), None

        existing_result = (
            supabase.table('reviews')
            .select('id,owner_token')
            .eq('id', review_id)
            .limit(1)
            .execute()
        )
        if not existing_result.data:
            return None, (jsonify({'error': 'Review not found.'}), 404)
        if owner_token and existing_result.data[0].get('owner_token') and existing_result.data[0]['owner_token'] != owner_token:
            return None, (jsonify({'error': 'Forbidden: you do not own this review.'}), 403)

        payload['updated_at'] = datetime.now(timezone.utc).isoformat()
        result = (
            supabase.table('reviews')
            .update(payload)
            .eq('id', review_id)
            .execute()
        )
        if not result.data:
            return None, (jsonify({'error': 'Review not found.'}), 404)
        return result.data[0], None

    @staticmethod
    def delete(review_id: int, owner_token: str | None = None) -> tuple | None:
        """Delete a review. Returns None on success or error response."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                existing = conn.execute(
                    'SELECT OWNER_TOKEN FROM REVIEWS WHERE ID = ?', (review_id,)
                ).fetchone()
                if not existing:
                    return jsonify({'error': 'Review not found.'}), 404
                if owner_token and existing['OWNER_TOKEN'] and existing['OWNER_TOKEN'] != owner_token:
                    return jsonify({'error': 'Forbidden: you do not own this review.'}), 403
                conn.execute('DELETE FROM REVIEWS WHERE ID = ?', (review_id,))
            return None

        if use_postgres():
            with pg_connection() as conn, conn.cursor() as cur:
                cur.execute('SELECT OWNER_TOKEN FROM REVIEWS WHERE ID = %s', (review_id,))
                existing = cur.fetchone()
                if not existing:
                    return jsonify({'error': 'Review not found.'}), 404
                if owner_token and existing[0] and existing[0] != owner_token:
                    return jsonify({'error': 'Forbidden: you do not own this review.'}), 403
                cur.execute('DELETE FROM REVIEWS WHERE ID = %s', (review_id,))
            return None

        existing = (
            supabase.table('reviews')
            .select('id,owner_token')
            .eq('id', review_id)
            .limit(1)
            .execute()
        )
        if not existing.data:
            return jsonify({'error': 'Review not found.'}), 404
        if owner_token and existing.data[0].get('owner_token') and existing.data[0]['owner_token'] != owner_token:
            return jsonify({'error': 'Forbidden: you do not own this review.'}), 403
        supabase.table('reviews').delete().eq('id', review_id).execute()
        return None

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

        if use_postgres():
            with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    '''SELECT MODULE_CODE,
                              ROUND(AVG(RATING)::numeric, 2) AS AVERAGE_RATING,
                              COUNT(*) AS REVIEW_COUNT,
                              SUM(CASE WHEN RATING = 5 THEN 1 ELSE 0 END) AS RATING_5_COUNT,
                              SUM(CASE WHEN RATING = 4 THEN 1 ELSE 0 END) AS RATING_4_COUNT,
                              SUM(CASE WHEN RATING = 3 THEN 1 ELSE 0 END) AS RATING_3_COUNT,
                              SUM(CASE WHEN RATING = 2 THEN 1 ELSE 0 END) AS RATING_2_COUNT,
                              SUM(CASE WHEN RATING = 1 THEN 1 ELSE 0 END) AS RATING_1_COUNT
                       FROM REVIEWS GROUP BY MODULE_CODE ORDER BY MODULE_CODE'''
                )
                rows = cur.fetchall()
            return {
                row['MODULE_CODE']: {
                    'average_rating': float(row['AVERAGE_RATING']),
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

        # Aggregate in-memory instead of GROUP BY — avoids Supabase
        # restrictions on aggregate queries with the free tier.
        try:
            result = supabase.table('reviews').select('module_code,rating').execute()
            grouped = {}
            for review in result.data:
                code = review['module_code']
                grouped.setdefault(code, []).append(review['rating'])
            return {
                code: {
                    'average_rating': round(sum(ratings) / len(ratings), 2),
                    'review_count': len(ratings),
                    'distribution': {
                        str(rating): ratings.count(rating)
                        for rating in range(5, 0, -1)
                    },
                }
                for code, ratings in grouped.items()
            }
        except APIError:
            return {}
# ---------------------------------------------------------------------------

class VoteRepository:
    """Handles vote persistence for SQLite, PostgreSQL, and Supabase."""

    @staticmethod
    def get_votes(review_id: int) -> dict:
        """Return vote score and user's vote for a review."""
        owner_token = _owner_token_from_request()

        if use_sqlite_reviews():
            with database_connection() as conn:
                row = conn.execute(
                    '''SELECT COALESCE(SUM(VOTE_TYPE), 0) as score
                       FROM REVIEW_VOTES WHERE REVIEW_ID = ?''',
                    (review_id,),
                ).fetchone()
                score = row['score'] if row else 0

                user_vote = 0
                if owner_token:
                    row = conn.execute(
                        '''SELECT VOTE_TYPE FROM REVIEW_VOTES
                           WHERE REVIEW_ID = ? AND OWNER_TOKEN = ?''',
                        (review_id, owner_token),
                    ).fetchone()
                    if row:
                        user_vote = row['VOTE_TYPE']
            return {'score': score, 'user_vote': user_vote}

        if use_postgres():
            with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    '''SELECT COALESCE(SUM(VOTE_TYPE), 0) as score
                       FROM REVIEW_VOTES WHERE REVIEW_ID = %s''',
                    (review_id,),
                )
                row = cur.fetchone()
                score = row['score'] if row else 0

                user_vote = 0
                if owner_token:
                    cur.execute(
                        '''SELECT VOTE_TYPE FROM REVIEW_VOTES
                           WHERE REVIEW_ID = %s AND OWNER_TOKEN = %s''',
                        (review_id, owner_token),
                    )
                    row = cur.fetchone()
                    if row:
                        user_vote = row['VOTE_TYPE']
            return {'score': score, 'user_vote': user_vote}

        try:
            result = (
                supabase.table('review_votes')
                .select('vote_type')
                .eq('review_id', review_id)
                .execute()
            )
            score = sum(v['vote_type'] for v in result.data) if result.data else 0

            user_vote = 0
            if owner_token:
                user_result = (
                    supabase.table('review_votes')
                    .select('vote_type')
                    .eq('review_id', review_id)
                    .eq('owner_token', owner_token)
                    .limit(1)
                    .execute()
                )
                if user_result.data:
                    user_vote = user_result.data[0]['vote_type']
            return {'score': score, 'user_vote': user_vote}
        except APIError:
            return {'score': 0, 'user_vote': 0}

    @staticmethod
    def get_votes_bulk(review_ids: list) -> dict:
        """Return vote scores for multiple reviews at once."""
        if not review_ids:
            return {}

        owner_token = _owner_token_from_request()

        if use_sqlite_reviews():
            with database_connection() as conn:
                placeholders = ','.join('?' * len(review_ids))
                rows = conn.execute(
                    f'''SELECT REVIEW_ID, COALESCE(SUM(VOTE_TYPE), 0) as score
                        FROM REVIEW_VOTES WHERE REVIEW_ID IN ({placeholders})
                        GROUP BY REVIEW_ID''',
                    review_ids,
                ).fetchall()
                scores = {row['REVIEW_ID']: row['score'] for row in rows}

                user_votes = {}
                if owner_token:
                    rows = conn.execute(
                        f'''SELECT REVIEW_ID, VOTE_TYPE FROM REVIEW_VOTES
                            WHERE REVIEW_ID IN ({placeholders}) AND OWNER_TOKEN = ?''',
                        (*review_ids, owner_token),
                    ).fetchall()
                    user_votes = {row['REVIEW_ID']: row['VOTE_TYPE'] for row in rows}

            return {
                rid: {
                    'score': scores.get(rid, 0),
                    'user_vote': user_votes.get(rid, 0),
                }
                for rid in review_ids
            }

        if use_postgres():
            with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                placeholders = ','.join(['%s'] * len(review_ids))
                cur.execute(
                    f'''SELECT REVIEW_ID, COALESCE(SUM(VOTE_TYPE), 0) as score
                        FROM REVIEW_VOTES WHERE REVIEW_ID IN ({placeholders})
                        GROUP BY REVIEW_ID''',
                    review_ids,
                )
                rows = cur.fetchall()
                scores = {row['REVIEW_ID']: row['score'] for row in rows}

                user_votes = {}
                if owner_token:
                    cur.execute(
                        f'''SELECT REVIEW_ID, VOTE_TYPE FROM REVIEW_VOTES
                            WHERE REVIEW_ID IN ({placeholders}) AND OWNER_TOKEN = %s''',
                        (*review_ids, owner_token),
                    )
                    rows = cur.fetchall()
                    user_votes = {row['REVIEW_ID']: row['VOTE_TYPE'] for row in rows}

            return {
                rid: {
                    'score': scores.get(rid, 0),
                    'user_vote': user_votes.get(rid, 0),
                }
                for rid in review_ids
            }

        try:
            result = (
                supabase.table('review_votes')
                .select('review_id,vote_type,owner_token')
                .in_('review_id', review_ids)
                .execute()
            )
            scores = {}
            user_votes = {}
            for v in result.data:
                rid = v['review_id']
                scores[rid] = scores.get(rid, 0) + v['vote_type']
                if owner_token and v.get('owner_token') == owner_token:
                    user_votes[rid] = v['vote_type']

            return {
                rid: {
                    'score': scores.get(rid, 0),
                    'user_vote': user_votes.get(rid, 0),
                }
                for rid in review_ids
            }
        except APIError:
            return {rid: {'score': 0, 'user_vote': 0} for rid in review_ids}

    @staticmethod
    def vote(review_id: int, vote_type: int) -> tuple:
        """Add or update a vote. Returns (result_dict, error_response)."""
        owner_token = _owner_token_from_request()
        if not owner_token:
            return None, (jsonify({'error': 'Authentication required.'}), 401)

        if vote_type not in (1, -1):
            return None, (jsonify({'error': 'Vote type must be 1 or -1.'}), 400)

        if use_sqlite_reviews():
            with database_connection() as conn:
                existing = conn.execute(
                    'SELECT ID, VOTE_TYPE FROM REVIEW_VOTES WHERE REVIEW_ID = ? AND OWNER_TOKEN = ?',
                    (review_id, owner_token),
                ).fetchone()

                if existing:
                    if existing['VOTE_TYPE'] == vote_type:
                        conn.execute('DELETE FROM REVIEW_VOTES WHERE ID = ?', (existing['ID'],))
                        return {'action': 'removed', 'vote_type': 0}, None
                    conn.execute(
                        'UPDATE REVIEW_VOTES SET VOTE_TYPE = ? WHERE ID = ?',
                        (vote_type, existing['ID']),
                    )
                    return {'action': 'updated', 'vote_type': vote_type}, None

                conn.execute(
                    'INSERT INTO REVIEW_VOTES (REVIEW_ID, OWNER_TOKEN, VOTE_TYPE) VALUES (?, ?, ?)',
                    (review_id, owner_token, vote_type),
                )
                return {'action': 'added', 'vote_type': vote_type}, None

        if use_postgres():
            with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    'SELECT ID, VOTE_TYPE FROM REVIEW_VOTES WHERE REVIEW_ID = %s AND OWNER_TOKEN = %s',
                    (review_id, owner_token),
                )
                existing = cur.fetchone()

                if existing:
                    if existing['VOTE_TYPE'] == vote_type:
                        cur.execute('DELETE FROM REVIEW_VOTES WHERE ID = %s', (existing['ID'],))
                        return {'action': 'removed', 'vote_type': 0}, None
                    cur.execute(
                        'UPDATE REVIEW_VOTES SET VOTE_TYPE = %s WHERE ID = %s',
                        (vote_type, existing['ID']),
                    )
                    return {'action': 'updated', 'vote_type': vote_type}, None

                cur.execute(
                    'INSERT INTO REVIEW_VOTES (REVIEW_ID, OWNER_TOKEN, VOTE_TYPE) VALUES (%s, %s, %s)',
                    (review_id, owner_token, vote_type),
                )
                return {'action': 'added', 'vote_type': vote_type}, None

        try:
            existing = (
                supabase.table('review_votes')
                .select('id,vote_type')
                .eq('review_id', review_id)
                .eq('owner_token', owner_token)
                .limit(1)
                .execute()
            )

            if existing.data:
                if existing.data[0]['vote_type'] == vote_type:
                    supabase.table('review_votes').delete().eq('id', existing.data[0]['id']).execute()
                    return {'action': 'removed', 'vote_type': 0}, None
                supabase.table('review_votes').update({'vote_type': vote_type}).eq('id', existing.data[0]['id']).execute()
                return {'action': 'updated', 'vote_type': vote_type}, None

            supabase.table('review_votes').insert({
                'review_id': review_id,
                'owner_token': owner_token,
                'vote_type': vote_type,
            }).execute()
            return {'action': 'added', 'vote_type': vote_type}, None
        except APIError as e:
            return None, (jsonify({'error': str(e)}), 500)


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Module data caching
# ---------------------------------------------------------------------------

# Simple TTL cache to avoid hitting Supabase rate limits on every keystroke.
_modules_cache = {'data': None, 'timestamp': 0}
MODULE_CACHE_TTL = 300  # 5 minutes


_CAREER_PATHS_TABLE = 'rp_career_paths'
_LOCAL_DATA_DIR = os.path.join(_base_dir, 'app', 'static', 'local-data', 'data')


def _load_local_modules() -> list[dict] | None:
    """Load module data from local JSON files when Supabase is unreachable."""
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
    """Load course/diploma data from local JSON file when Supabase is unreachable."""
    courses_path = os.path.join(_LOCAL_DATA_DIR, 'rp_courses.json')
    try:
        with open(courses_path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _load_local_minors() -> list[dict] | None:
    """Load minor programme data from local JSON file when Supabase is unreachable."""
    minors_path = os.path.join(_LOCAL_DATA_DIR, 'rp_minors.json')
    try:
        with open(minors_path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _build_modules_list() -> list | None:
    """Fetch modules from Supabase, falling back to local JSON files."""
    if supabase is not None:
        try:
            result = supabase.table("rp_modules").select("*").order("module_code").execute()
            return [{
                "code": row.get("module_code", ""),
                "name": row.get("module_name", ""),
                "synopsis": row.get("synopsis", ""),
                "school": row.get("school_name", ""),
                "school_abbr": row.get("school_abbr", ""),
                "url": row.get("url", ""),
            } for row in result.data]
        except APIError:
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


# ---------------------------------------------------------------------------
# Routes - Page serving
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Routes - API endpoints
# ---------------------------------------------------------------------------

@app.route('/api/modules', methods=['GET'])
def get_modules():
    """Return all modules from Supabase with generated comparison fields.

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
    """Return all courses (diplomas) from Supabase rp_courses table."""
    now = time.time()
    if _courses_cache['data'] is not None and (now - _courses_cache['timestamp']) < COURSES_CACHE_TTL:
        return jsonify(_courses_cache['data']), 200

    courses = None
    if supabase is not None:
        try:
            result = supabase.table('rp_courses').select('*').execute()
            courses = result.data
        except APIError:
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
    """Return all minor programmes from Supabase rp_minors table."""
    now = time.time()
    if _minors_cache['data'] is not None and (now - _minors_cache['timestamp']) < MINORS_CACHE_TTL:
        return jsonify(_minors_cache['data']), 200

    minors = None
    if supabase is not None:
        try:
            result = supabase.table('rp_minors').select('*').execute()
            minors = result.data
        except APIError:
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
    reviews = ReviewRepository.list_all()
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

    owner_token = _owner_token_from_request()
    if owner_token:
        payload['owner_token'] = owner_token

    review, error_response = ReviewRepository.create(payload)
    if error_response:
        return error_response
    return jsonify(review), 201


@app.route('/api/reviews/<module_code>', methods=['GET'])
def get_reviews(module_code):
    """Return all reviews for a specific module code."""
    reviews = ReviewRepository.list_by_module(module_code)
    return jsonify(reviews), 200


@app.route('/api/reviews/<int:review_id>', methods=['PUT'])
@limiter.limit("10/hour")
def update_review(review_id):
    """Update an existing review by ID."""
    payload, error = validate_review_payload(request.get_json(silent=True))
    if error:
        return jsonify({'error': error}), 400

    review, error_response = ReviewRepository.update(review_id, payload, _owner_token_from_request())
    if error_response:
        return error_response
    return jsonify(review), 200


@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@limiter.limit("10/hour")
def delete_review(review_id):
    """Delete a review by ID."""
    error_response = ReviewRepository.delete(review_id, _owner_token_from_request())
    if error_response:
        return error_response
    return '', 204


@app.route('/api/reviews/<int:review_id>/vote', methods=['GET'])
def get_review_votes(review_id):
    """Return vote score and user's vote for a review."""
    votes = VoteRepository.get_votes(review_id)
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

    result, error_response = VoteRepository.vote(review_id, vote_type)
    if error_response:
        return error_response
    return jsonify(result), 200


@app.route('/api/reviews/<int:review_id>/vote', methods=['DELETE'])
@limiter.limit("30/hour")
def remove_review_vote(review_id):
    """Remove a user's vote from a review."""
    owner_token = _owner_token_from_request()
    if not owner_token:
        return jsonify({'error': 'Authentication required.'}), 401

    if use_sqlite_reviews():
        with database_connection() as conn:
            conn.execute(
                'DELETE FROM REVIEW_VOTES WHERE REVIEW_ID = ? AND OWNER_TOKEN = ?',
                (review_id, owner_token),
            )
    elif use_postgres():
        with pg_connection() as conn, conn.cursor() as cur:
            cur.execute(
                'DELETE FROM REVIEW_VOTES WHERE REVIEW_ID = %s AND OWNER_TOKEN = %s',
                (review_id, owner_token),
            )
    else:
        supabase.table('review_votes').delete().eq('review_id', review_id).eq('owner_token', owner_token).execute()

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

    votes = VoteRepository.get_votes_bulk(review_ids)
    return jsonify(votes), 200


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
    if supabase is not None:
        try:
            result = supabase.table("rp_courses").select("*").execute()
            courses = result.data
        except APIError:
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

    # 1. Exact module code match
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

    # 2. Greeting
    if re.match(r'^(hi|hello|hey|howdy|yo|sup)\b', msg_lower):
        return jsonify({
            "reply": "Hi! Tell me what career or interests you're exploring, and I'll recommend modules for you!",
            "links": [],
            "suggestions": ["I like designing websites", "I want to build software", "Tell me about careers"],
        })

    # 3. Reviews lookup
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

    # 4. Navigation / help
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

    # 5. About ModuleGo
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
    """Load career paths from DB (SQLite/PostgreSQL/Supabase), with file + hardcoded fallback."""
    # SQLite path (dev/test)
    if use_sqlite_reviews():
        try:
            with database_connection() as conn:
                rows = conn.execute(
                    'SELECT CAREER_ID, LABEL, KEYWORDS FROM CAREER_PATHS ORDER BY ID'
                ).fetchall()
                if rows:
                    return [{'id': r[0], 'label': r[1], 'keywords': json.loads(r[2])} for r in rows]
        except (sqlite3.Error, json.JSONDecodeError):
            pass
        paths = _load_career_paths_from_file()
        if paths:
            return paths
        return _CAREER_FALLBACK

    # PostgreSQL path
    if use_postgres():
        try:
            with pg_connection() as conn, conn.cursor() as cur:
                cur.execute('SELECT CAREER_ID, LABEL, KEYWORDS FROM CAREER_PATHS ORDER BY ID')
                rows = cur.fetchall()
                if rows:
                    return [{'id': r[0], 'label': r[1], 'keywords': json.loads(r[2])} for r in rows]
        except (psycopg2.Error, json.JSONDecodeError):
            pass
        paths = _load_career_paths_from_file()
        if paths:
            return paths
        return _CAREER_FALLBACK

    # Supabase path (production)
    try:
        result = supabase.table(_CAREER_PATHS_TABLE).select('*').order('id').execute()
        if result.data:
            return [{'id': r['id'], 'label': r['label'], 'keywords': r['keywords']} for r in result.data]
    except APIError:
        pass

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
# CSRF exemptions for API endpoints (custom-header auth pattern)
# ---------------------------------------------------------------------------

csrf.exempt(get_modules)
csrf.exempt(get_courses)
csrf.exempt(list_reviews)
csrf.exempt(get_reviews)
csrf.exempt(get_rating_summaries)
csrf.exempt(generate_comparison)
csrf.exempt(get_career_paths)
csrf.exempt(gobot_chat)
csrf.exempt(add_review)
csrf.exempt(update_review)
csrf.exempt(delete_review)
csrf.exempt(get_review_votes)
csrf.exempt(vote_review)
csrf.exempt(remove_review_vote)
csrf.exempt(get_bulk_votes)


if __name__ == '__main__':
    print("ModuleGo Backend Server running on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

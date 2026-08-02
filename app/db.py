"""Database connection helpers and row mappers.

Provides dual-backend (SQLite / PostgreSQL) connection factories,
row converters, and schema initialisation used across the application.
"""

import json
import os
import sqlite3
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from flask import current_app


def use_sqlite_reviews():
    try:
        if current_app.config.get('TESTING'):
            return True
    except RuntimeError:
        pass
    return not os.environ.get('DATABASE_URL')


def use_postgres():
    try:
        if current_app.config.get('TESTING'):
            return False
    except RuntimeError:
        pass
    return bool(os.environ.get('DATABASE_URL'))


def get_db():
    import app as _app
    conn = sqlite3.connect(_app.db_name)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def database_connection():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_pg_db():
    conn = psycopg2.connect(current_app.config['DATABASE_URL'])
    conn.autocommit = False
    return conn


@contextmanager
def pg_connection():
    conn = get_pg_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_value(row, key, default=None):
    """Read a value from a DB row, handling SQLite/PostgreSQL column casing.

    SQLite Row objects return UPPERCASE column names; PostgreSQL RealDictCursor
    returns lowercase. This function tries both casings for compatibility.
    """
    try:
        return row[key]
    except (KeyError, IndexError):
        try:
            return row[key.upper()]
        except (KeyError, IndexError):
            return default


def review_to_dict(row) -> dict:
    return {
        'id': _row_value(row, 'id'),
        'module_code': _row_value(row, 'module_code'),
        'rating': _row_value(row, 'rating'),
        'comment': _row_value(row, 'comment', ''),
        'created_at': _row_value(row, 'created_at'),
        'updated_at': _row_value(row, 'updated_at'),
        'user_id': _row_value(row, 'user_id'),
        'guest_owner_hash': _row_value(row, 'guest_owner_hash'),
        'is_anonymous': bool(_row_value(row, 'is_anonymous', True)),
        'author_display_name': _row_value(row, 'author_display_name'),
    }


def public_review(row, identity=None) -> dict:
    from app.core import identity_owns

    review = review_to_dict(row)
    is_owner = identity_owns(review, identity)
    anonymous = (
        not review['user_id']
        or review['is_anonymous']
        or not review['author_display_name']
    )
    return {
        'id': review['id'],
        'module_code': review['module_code'],
        'rating': review['rating'],
        'comment': review['comment'],
        'created_at': review['created_at'],
        'updated_at': review['updated_at'],
        'is_owner': is_owner,
        'author': {
            'anonymous': anonymous,
            'label': (
                'Anonymous student'
                if anonymous
                else review['author_display_name']
            ),
        },
    }


def select_review(conn, review_id: int):
    return conn.execute(
        '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT, UPDATED_AT,
                  USER_ID, GUEST_OWNER_HASH, IS_ANONYMOUS,
                  AUTHOR_DISPLAY_NAME
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


def _load_career_paths_from_file() -> list | None:
    local_data_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'static', 'local-data', 'data'
    )
    path = os.path.join(local_data_dir, 'rp_career_paths.json')
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _seed_career_paths() -> None:
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

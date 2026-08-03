"""Core business logic: ownership, repositories, Gemini, GoBot.

Central module for identity management, review/vote/bookmark persistence,
AI-powered comparison generation, and the GoBot chatbot.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3

import psycopg2
import psycopg2.extras
import requests
from flask import current_app, g, request
from flask_login import current_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.db import (
    database_connection,
    pg_connection,
    public_review,
    review_to_dict,
    select_review,
    use_postgres,
    use_sqlite_reviews,
)

GUEST_COOKIE_NAME = "modulego_guest"
GUEST_COOKIE_MAX_AGE = 30 * 24 * 60 * 60
MAX_COMMENT_LENGTH = 500
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.1-flash-lite')
GEMINI_TIMEOUT_SECONDS = 25
MAX_COMPARISON_SOURCE_LENGTH = 4000
_CAREER_PATHS_TABLE = 'rp_career_paths'
MIMETYPE_JSON = 'application/json'
MSG_REVIEW_NOT_FOUND = 'Review not found.'
MSG_FORBIDDEN = 'Forbidden: you do not own this review.'
SQL_SELECT_REVIEW_BY_ID_SQLITE = 'SELECT * FROM REVIEWS WHERE ID = ?'
SQL_SELECT_REVIEW_BY_ID_PG = 'SELECT * FROM REVIEWS WHERE ID = %s'

_base_dir = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(_base_dir, 'static', 'local-data', 'data')


# ---------------------------------------------------------------------------
# Ownership helpers
# ---------------------------------------------------------------------------

def _serializer():
    return URLSafeTimedSerializer(
        current_app.secret_key,
        salt="modulego-guest-ownership-v1",
    )


def _hash_guest_id(guest_id):
    return hmac.new(
        current_app.secret_key.encode("utf-8"),
        guest_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def current_guest_hash():
    signed_value = request.cookies.get(GUEST_COOKIE_NAME, "")
    if not signed_value:
        return None
    try:
        guest_id = _serializer().loads(
            signed_value,
            max_age=GUEST_COOKIE_MAX_AGE,
        )
    except (BadSignature, SignatureExpired):
        return None
    return _hash_guest_id(guest_id)


def request_identity(create_guest=False):
    if current_user.is_authenticated:
        return {
            "kind": "account",
            "user_id": current_user.id,
            "guest_owner_hash": None,
            "display_name": getattr(current_user, "display_name", "Student")[:50],
        }
    guest_hash = current_guest_hash()
    if not guest_hash and create_guest:
        guest_id = secrets.token_urlsafe(32)
        guest_hash = _hash_guest_id(guest_id)
        g.pending_guest_cookie = _serializer().dumps(guest_id)
    if guest_hash:
        return {
            "kind": "guest",
            "user_id": None,
            "guest_owner_hash": guest_hash,
            "display_name": None,
        }
    return None


def rotate_guest_cookie():
    guest_id = secrets.token_urlsafe(32)
    g.pending_guest_cookie = _serializer().dumps(guest_id)


def set_pending_guest_cookie(response):
    signed_value = getattr(g, "pending_guest_cookie", None)
    if signed_value:
        response.set_cookie(
            GUEST_COOKIE_NAME,
            signed_value,
            max_age=GUEST_COOKIE_MAX_AGE,
            httponly=True,
            secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
            samesite="Lax",
            path="/",
        )
    return response


def identity_owns(row, identity):
    if not identity:
        return False
    if identity["kind"] == "account":
        if row.get("user_id") and str(row["user_id"]) == identity["user_id"]:
            return True
        guest_hash = current_guest_hash()
        if guest_hash and row.get("guest_owner_hash"):
            return hmac.compare_digest(row["guest_owner_hash"], guest_hash)
        return False
    return bool(
        row.get("guest_owner_hash")
        and hmac.compare_digest(
            row["guest_owner_hash"],
            identity["guest_owner_hash"],
        )
    )


# ---------------------------------------------------------------------------
# Review Repository
# ---------------------------------------------------------------------------

class ReviewRepository:

    @staticmethod
    def list_all(identity=None) -> list:
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
                return None, (current_app.response_class(
                    json.dumps({'error': 'You already reviewed this module.'}),
                    status=409, mimetype=MIMETYPE_JSON
                ))
            raise

    @staticmethod
    def update(review_id: int, payload: dict, identity: dict) -> tuple:
        if use_sqlite_reviews():
            with database_connection() as conn:
                existing = conn.execute(
                    SQL_SELECT_REVIEW_BY_ID_SQLITE, (review_id,)
                ).fetchone()
                if not existing:
                    return None, (current_app.response_class(
                        json.dumps({'error': MSG_REVIEW_NOT_FOUND}),
                        status=404, mimetype=MIMETYPE_JSON
                    ))
                if not identity_owns(review_to_dict(existing), identity):
                    return None, (current_app.response_class(
                        json.dumps({'error': MSG_FORBIDDEN}),
                        status=403, mimetype=MIMETYPE_JSON
                    ))
                existing_dict = review_to_dict(existing)
                anonymous = ReviewRepository._determine_anonymous(identity, existing_dict, payload)
                if ReviewRepository._should_migrate(identity, existing_dict):
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
            cur.execute(SQL_SELECT_REVIEW_BY_ID_PG, (review_id,))
            existing = cur.fetchone()
            if not existing:
                return None, (current_app.response_class(
                    json.dumps({'error': MSG_REVIEW_NOT_FOUND}),
                    status=404, mimetype=MIMETYPE_JSON
                ))
            if not identity_owns(review_to_dict(existing), identity):
                return None, (current_app.response_class(
                    json.dumps({'error': MSG_FORBIDDEN}),
                    status=403, mimetype=MIMETYPE_JSON
                ))
            existing_dict = review_to_dict(existing)
            anonymous = ReviewRepository._determine_anonymous(identity, existing_dict, payload)
            if ReviewRepository._should_migrate(identity, existing_dict):
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
            cur.execute(SQL_SELECT_REVIEW_BY_ID_PG, (review_id,))
            row = cur.fetchone()
        return public_review(row, identity), None

    @staticmethod
    def delete(review_id: int, identity: dict) -> tuple | None:
        if use_sqlite_reviews():
            with database_connection() as conn:
                existing = conn.execute(
                    SQL_SELECT_REVIEW_BY_ID_SQLITE, (review_id,)
                ).fetchone()
                if not existing:
                    return current_app.response_class(
                        json.dumps({'error': MSG_REVIEW_NOT_FOUND}),
                        status=404, mimetype=MIMETYPE_JSON
                    )
                if not identity_owns(review_to_dict(existing), identity):
                    return current_app.response_class(
                        json.dumps({'error': MSG_FORBIDDEN}),
                        status=403, mimetype=MIMETYPE_JSON
                    )
                conn.execute('DELETE FROM REVIEWS WHERE ID = ?', (review_id,))
            return None

        with pg_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_SELECT_REVIEW_BY_ID_PG, (review_id,))
            existing = cur.fetchone()
            if not existing:
                return current_app.response_class(
                    json.dumps({'error': MSG_REVIEW_NOT_FOUND}),
                    status=404, mimetype=MIMETYPE_JSON
                )
            if not identity_owns(review_to_dict(existing), identity):
                return current_app.response_class(
                    json.dumps({'error': MSG_FORBIDDEN}),
                    status=403, mimetype=MIMETYPE_JSON
                )
            cur.execute('DELETE FROM REVIEWS WHERE ID = %s', (review_id,))
        return None

    @staticmethod
    def update_author_display_name(user_id: str, display_name: str) -> int:
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
    def _determine_anonymous(identity, existing_data, payload):
        """Determine the anonymous flag for a review update."""
        if identity['kind'] == 'guest':
            return True
        return bool(payload.get('is_anonymous', existing_data.get('is_anonymous', True)))

    @staticmethod
    def _should_migrate(identity, existing_data):
        """Check if a guest review should be migrated to account ownership."""
        return (
            identity['kind'] == 'account'
            and not existing_data.get('user_id')
            and existing_data.get('guest_owner_hash')
        )

    @staticmethod
    def count_by_user(user_id: str) -> int:
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


# ---------------------------------------------------------------------------
# Vote Repository
# ---------------------------------------------------------------------------

class VoteRepository:

    @staticmethod
    def _identity_filter(identity):
        """Return the (column_name, value) tuple for the identity's ownership field."""
        if not identity:
            return None, None
        if identity['kind'] == 'account':
            return 'user_id', identity['user_id']
        return 'guest_owner_hash', identity['guest_owner_hash']

    @staticmethod
    def get_votes(review_id: int, identity=None) -> dict:
        return VoteRepository.get_votes_bulk([review_id], identity).get(
            review_id,
            {'score': 0, 'user_vote': 0},
        )

    @staticmethod
    def get_votes_bulk(review_ids: list, identity=None) -> dict:
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
                cur.execute(SQL_SELECT_REVIEW_BY_ID_PG, (review_id,))
                row = cur.fetchone()
        return row is not None and identity_owns(review_to_dict(row), identity)

    @staticmethod
    def vote(review_id: int, vote_type: int, identity: dict) -> tuple:
        if vote_type not in (1, -1):
            return None, (current_app.response_class(
                json.dumps({'error': 'Vote type must be 1 or -1.'}),
                status=400, mimetype=MIMETYPE_JSON
            ))
        if VoteRepository._review_owned(review_id, identity):
            return None, (current_app.response_class(
                json.dumps({'error': 'You cannot vote on your own review.'}),
                status=403, mimetype=MIMETYPE_JSON
            ))
        column, value = VoteRepository._identity_filter(identity)

        if use_sqlite_reviews():
            with database_connection() as conn:
                review = conn.execute(
                    'SELECT ID FROM REVIEWS WHERE ID = ?', (review_id,)
                ).fetchone()
                if not review:
                    return None, (current_app.response_class(
                        json.dumps({'error': MSG_REVIEW_NOT_FOUND}),
                        status=404, mimetype=MIMETYPE_JSON
                    ))
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
    def _write_sqlite_vote(conn, existing, review_id, vote_type, column, value):
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


# ---------------------------------------------------------------------------
# Bookmark Repository
# ---------------------------------------------------------------------------

class BookmarkRepository:

    @staticmethod
    def list_for_user(user_id):
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


# ---------------------------------------------------------------------------
# Ownership Repository
# ---------------------------------------------------------------------------

class OwnershipRepository:

    @staticmethod
    def pending_counts(guest_hash):
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
        with pg_connection() as conn, conn.cursor() as cur:
            cur.execute(
                'SELECT claim_guest_activity(%s, %s, %s, %s)',
                (
                    identity['user_id'], guest_hash,
                    identity['display_name'], codes,
                ),
            )
            return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_review_payload(data: dict | None, require_module_code: bool = False) -> tuple:
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
# Data loading helpers
# ---------------------------------------------------------------------------

def _load_local_modules() -> list[dict] | None:
    synopsis_path = os.path.join(LOCAL_DATA_DIR, 'rp_modules_synopsis.json')
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
    courses_path = os.path.join(LOCAL_DATA_DIR, 'rp_courses.json')
    try:
        with open(courses_path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _load_local_minors() -> list[dict] | None:
    minors_path = os.path.join(LOCAL_DATA_DIR, 'rp_minors.json')
    try:
        with open(minors_path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _load_career_paths_from_file() -> list | None:
    path = os.path.join(LOCAL_DATA_DIR, 'rp_career_paths.json')
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _build_modules_list() -> list | None:
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


# Per-process cache (not shared across Gunicorn workers). TTL-based staleness.
_modules_cache = {'data': None, 'timestamp': 0}
MODULE_CACHE_TTL = 300

_courses_cache = {'data': None, 'timestamp': 0}
COURSES_CACHE_TTL = 300

_minors_cache = {'data': None, 'timestamp': 0}
MINORS_CACHE_TTL = 300


# ---------------------------------------------------------------------------
# Gemini integration
# ---------------------------------------------------------------------------

class GeminiServiceError(RuntimeError):
    pass


def generate_gemini_comparison(modules: list[dict]) -> list[dict]:
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
        raise GeminiServiceError(
            'Gemini could not generate a comparison.'
        ) from error

    rows = generated.get('modules') if isinstance(generated, dict) else None
    if not isinstance(rows, list) or len(rows) != 2:
        raise GeminiServiceError('Gemini returned an invalid comparison.')
    return rows


# ---------------------------------------------------------------------------
# GoBot chatbot
# ---------------------------------------------------------------------------

# Common English words to ignore when extracting search keywords from user messages.
_CAREER_KEYWORD_STOPWORDS = frozenset({
    'what', 'where', 'when', 'which', 'why', 'this', 'that', 'with', 'want',
    'like', 'tell', 'show', 'how', 'can', 'for', 'the', 'and', 'are', 'you',
    'about', 'some', 'have', 'from', 'your', 'know', 'just', 'also', 'more',
    'any', 'all', 'not', 'get', 'use', 'could', 'would', 'does', 'there',
    'their', 'they', 'them', 'been', 'were', 'was', 'has', 'had', 'but',
    'its', 'into', 'than', 'then', 'very', 'will', 'got', 'say'
})

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


def _get_active_module_codes() -> frozenset:
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
    # Prompt design: constrains Gemini to return structured JSON with short text.
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


def load_career_paths() -> list:
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

"""Shared database helpers extracted from app.py.

Contains row converters and backend-selection helpers used by
ReviewRepository and other modules.  Connection lifecycle
(database_connection, init_db) stays in app.py so tests can
monkeypatch ``app_module.db_name`` and have it take effect.
"""

import os

_base_dir = os.path.dirname(os.path.abspath(__file__))


def use_sqlite_reviews():
    """True when SQLite should be used (tests or no DATABASE_URL)."""
    try:
        import flask
        if flask.current_app.config.get('TESTING'):
            return True
    except RuntimeError:
        pass
    return not os.environ.get('DATABASE_URL')


def use_postgres():
    """True when PostgreSQL should be used (DATABASE_URL set, not testing)."""
    try:
        import flask
        if flask.current_app.config.get('TESTING'):
            return False
    except RuntimeError:
        pass
    return bool(os.environ.get('DATABASE_URL'))


def _row_value(row, key, default=None):
    """Read a value from SQLite or PostgreSQL row mappings.

    Handles the casing mismatch: SQLite Row returns UPPERCASE keys,
    PostgreSQL RealDictCursor returns lowercase.
    """
    try:
        return row[key]
    except (KeyError, IndexError):
        try:
            return row[key.upper()]
        except (KeyError, IndexError):
            return default


def review_to_dict(row) -> dict:
    """Convert a database row to the internal review representation."""
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
    """Return a review without leaking private ownership fields.

    Public contract exposes ``is_owner`` and ``author.{anonymous, label}``
    only -- raw ``user_id`` / ``guest_owner_hash`` never leave this function.
    """
    from ownership import identity_owns

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
    """Fetch a single review by ID from SQLite."""
    return conn.execute(
        '''SELECT ID, MODULE_CODE, RATING, COMMENT, CREATED_AT, UPDATED_AT,
                  USER_ID, GUEST_OWNER_HASH, IS_ANONYMOUS,
                  AUTHOR_DISPLAY_NAME
           FROM REVIEWS WHERE ID = ?''',
        (review_id,),
    ).fetchone()

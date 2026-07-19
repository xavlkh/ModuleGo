"""ModuleGo Flask application.

Provides the backend API for module data and review management,
serving Republic Polytechnic students.
"""
from flask import Flask, request, jsonify, render_template
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
import json
import sqlite3
import os
import subprocess
import time
from dotenv import load_dotenv
from supabase import create_client
from postgrest.exceptions import APIError

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

csrf.init_app(app)
limiter.init_app(app)


def _get_commit_hash() -> str | None:
    """Return the short git commit hash, or None if unavailable."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, cwd=_base_dir, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
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
    return supabase is None


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
    """Create or upgrade the SQLite review table used locally and in tests."""
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


if use_sqlite_reviews():
    init_db()


# ---------------------------------------------------------------------------
# Review repository - encapsulates dual-database branching
# ---------------------------------------------------------------------------

class ReviewRepository:
    """Handles review persistence for both SQLite (tests) and Supabase."""

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

        try:
            result = supabase.table('reviews').insert({**payload, 'owner_token': owner_token}).execute()
        except APIError as error:
            if error.code == '23503':
                return None, (jsonify({'error': 'Module code does not exist.'}), 400)
            raise
        return result.data[0], None

    @staticmethod
    def update(review_id: int, payload: dict, owner_token: str = None) -> tuple:
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
    def delete(review_id: int, owner_token: str = None) -> tuple | None:
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
        """Return average rating and review count per module."""
        if use_sqlite_reviews():
            with database_connection() as conn:
                rows = conn.execute(
                    '''SELECT MODULE_CODE,
                              ROUND(AVG(RATING), 2) AS AVERAGE_RATING,
                              COUNT(*) AS REVIEW_COUNT
                       FROM REVIEWS GROUP BY MODULE_CODE ORDER BY MODULE_CODE'''
                ).fetchall()
            return {
                row['MODULE_CODE']: {
                    'average_rating': row['AVERAGE_RATING'],
                    'review_count': row['REVIEW_COUNT'],
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
                }
                for code, ratings in grouped.items()
            }
        except Exception:
            return {}


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


# ---------------------------------------------------------------------------
# Module data caching
# ---------------------------------------------------------------------------

# Simple TTL cache to avoid hitting Supabase rate limits on every keystroke.
_modules_cache = {'data': None, 'timestamp': 0}
MODULE_CACHE_TTL = 300  # 5 minutes


_LOCAL_DATA_DIR = os.path.join(_base_dir, 'app', 'static', 'local-data', 'data')


def _load_local_modules() -> list[dict] | None:
    """Load module data from local JSON files when Supabase is unreachable."""
    synopsis_path = os.path.join(_LOCAL_DATA_DIR, 'rp_modules_synopsis.json')
    comparison_path = os.path.join(_LOCAL_DATA_DIR, 'rp_modules_comparison.json')
    try:
        with open(synopsis_path, encoding='utf-8') as f:
            synopsis_data = {row['module_code']: row for row in json.load(f)}
        with open(comparison_path, encoding='utf-8') as f:
            comparison_data = {row['module_code']: row for row in json.load(f)}
    except (OSError, KeyError, json.JSONDecodeError):
        return None

    modules = []
    for code, syn in synopsis_data.items():
        comp = comparison_data.get(code, {})
        modules.append({
            'code': code,
            'name': syn.get('module_name', ''),
            'synopsis': syn.get('synopsis', ''),
            'school': syn.get('school_name', ''),
            'school_abbr': syn.get('school_abbr', ''),
            'url': syn.get('url', ''),
            'summary': comp.get('summary', ''),
            'suitableFor': comp.get('suitable_for', ''),
        })
    return modules


def _load_local_courses() -> list[dict] | None:
    """Load course/diploma data from local JSON file when Supabase is unreachable."""
    courses_path = os.path.join(_LOCAL_DATA_DIR, 'rp_courses.json')
    try:
        with open(courses_path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _build_modules_list() -> list | None:
    """Fetch modules from Supabase, falling back to local JSON files."""
    if supabase is not None:
        try:
            result = supabase.table("rp_modules").select("*").order("module_code").execute()
            sf_result = supabase.table("rp_modules_comparision").select("*").execute()
            sf_map = {row["module_code"]: row for row in sf_result.data}
            modules = []
            for row in result.data:
                code = row.get("module_code", "")
                module = {
                    "code": code,
                    "name": row.get("module_name", ""),
                    "synopsis": row.get("synopsis", ""),
                    "school": row.get("school_name", ""),
                    "school_abbr": row.get("school_abbr", ""),
                    "url": row.get("url", ""),
                }
                sf_row = sf_map.get(code, {})
                module["summary"] = sf_row.get("summary", "")
                module["suitableFor"] = sf_row.get("suitable_for", "")
                modules.append(module)
            return modules
        except Exception:
            pass
    return _load_local_modules()


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
        except Exception:
            pass

    if courses is None:
        courses = _load_local_courses()

    if courses is None:
        return jsonify({'error': 'No course data available.'}), 503

    _courses_cache['data'] = courses
    _courses_cache['timestamp'] = now
    return jsonify(courses), 200


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

    owner_token = request.headers.get('X-Owner-Token', '').strip()
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

    owner_token = request.headers.get('X-Owner-Token', '').strip() or None
    review, error_response = ReviewRepository.update(review_id, payload, owner_token)
    if error_response:
        return error_response
    return jsonify(review), 200


@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@limiter.limit("10/hour")
def delete_review(review_id):
    """Delete a review by ID."""
    owner_token = request.headers.get('X-Owner-Token', '').strip() or None
    error_response = ReviewRepository.delete(review_id, owner_token)
    if error_response:
        return error_response
    return '', 204


@app.route('/api/ratings', methods=['GET'])
def get_rating_summaries():
    """Return average rating and review count for each module."""
    summaries = ReviewRepository.rating_summaries()
    return jsonify(summaries), 200


# ---------------------------------------------------------------------------
# CSRF exemptions for API endpoints (custom-header auth pattern)
# ---------------------------------------------------------------------------

csrf.exempt(get_modules)
csrf.exempt(get_courses)
csrf.exempt(list_reviews)
csrf.exempt(get_reviews)
csrf.exempt(get_rating_summaries)
csrf.exempt(add_review)
csrf.exempt(update_review)
csrf.exempt(delete_review)


if __name__ == '__main__':
    print("ModuleGo Backend Server running on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

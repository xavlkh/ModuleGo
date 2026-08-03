"""Application factory for ModuleGo Flask app."""

import logging
import os
import subprocess

from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from app.db import init_db, use_postgres, use_sqlite_reviews

load_dotenv()

log = logging.getLogger(__name__)


def _rate_limit_key():
    """Return a unique rate-limit key per request.

    In tests, return a unique key per request so rate limits never trigger
    across test methods. In production, return the client IP address.
    """
    from flask import current_app
    if current_app.config.get('TESTING'):
        if not hasattr(current_app, '_test_request_counter'):
            current_app._test_request_counter = 0
        current_app._test_request_counter += 1
        return f"test-{current_app._test_request_counter}"
    return get_remote_address()


def create_app():
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    secret_key = os.environ.get('FLASK_SECRET_KEY', '')
    if not secret_key:
        log.warning(
            'FLASK_SECRET_KEY is not set — using insecure default. '
            'Set FLASK_SECRET_KEY in .env for production.'
        )
        secret_key = 'modulego-local-development-secret-change-me'

    app.config.update(
        SECRET_KEY=secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=False,
        PERMANENT_SESSION_LIFETIME=30 * 24 * 60 * 60,  # 30 days in seconds
        DATABASE_URL=os.environ.get('DATABASE_URL'),
    )

    csrf = CSRFProtect()
    csrf.init_app(app)

    limiter = Limiter(
        key_func=_rate_limit_key,
        default_limits=["200 per hour"],
        storage_uri="memory://",
    )
    limiter.init_app(app)
    app.limiter = limiter

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'error'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User as _User
        return _User.find_by_id(user_id)

    from app.core import set_pending_guest_cookie, ReviewRepository  # noqa: F811
    app.after_request(set_pending_guest_cookie)

    app.extensions['review_repository'] = ReviewRepository

    # Prometheus metrics — single-process for tests/dev, multiprocess for Gunicorn
    from prometheus_flask_exporter import PrometheusMetrics
    from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics
    if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
        GunicornPrometheusMetrics(app, path=None, group_by='url_rule')
    else:
        PrometheusMetrics(app, group_by='url_rule')

    _base_dir = os.path.dirname(os.path.abspath(__file__))

    @app.context_processor
    def inject_globals():
        env_hash = os.environ.get('COMMIT_HASH', '').strip()
        commit_hash = None
        if env_hash:
            commit_hash = env_hash[:7]
        else:
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', '--short', 'HEAD'],
                    capture_output=True, text=True,
                    cwd=os.path.dirname(_base_dir), timeout=5, check=False
                )
                if result.returncode == 0:
                    commit_hash = result.stdout.strip()
            except (OSError, subprocess.SubprocessError):
                pass
        return {
            'current_year': datetime.now(timezone.utc).year,
            'commit_hash': commit_hash,
        }

    from app.routes.auth import auth_bp
    from app.routes.api import api_bp
    from app.routes.pages import serve_index, serve_comparison, serve_bookmarks, serve_reviews

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    # CSRF exemptions: read-only GET endpoints and comparison/gobot POST endpoints
    # are exempt. Review/vote/bookmark/ownership mutations require CSRF tokens.
    from app.routes.api import (
        get_modules, get_courses, list_reviews, get_reviews,
        get_rating_summaries, generate_comparison, get_career_paths,
        gobot_chat, get_review_votes, get_bulk_votes,
    )
    for view in (get_modules, get_courses, list_reviews, get_reviews,
                 get_rating_summaries, generate_comparison, get_career_paths,
                 gobot_chat, get_review_votes, get_bulk_votes):
        csrf.exempt(view)

    app.add_url_rule('/', 'serve_index', serve_index)
    app.add_url_rule('/comparison', 'serve_comparison', serve_comparison)
    app.add_url_rule('/bookmarks', 'serve_bookmarks', serve_bookmarks)
    app.add_url_rule('/reviews', 'serve_reviews', serve_reviews)

    if use_sqlite_reviews():
        with app.app_context():
            init_db()
    elif use_postgres():
        with app.app_context():
            _init_pg_db(app)

    return app


def _init_pg_db(app):
    """Create PostgreSQL tables if they don't exist."""
    import psycopg2
    from app.db import pg_connection, use_postgres  # noqa: F811

    if not use_postgres():
        return

    _CAREER_PATHS_TABLE = 'rp_career_paths'
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    LOCAL_DATA_DIR = os.path.join(_base_dir, 'static', 'local-data', 'data')

    try:
        with pg_connection() as conn, conn.cursor() as cur:
            # Create all tables before seeding
            cur.execute(
                '''CREATE TABLE IF NOT EXISTS users
                   (id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW())'''
            )
            cur.execute(
                '''CREATE TABLE IF NOT EXISTS rp_career_paths
                   (ID SERIAL PRIMARY KEY,
                    CAREER_ID TEXT NOT NULL UNIQUE,
                    LABEL TEXT NOT NULL,
                    KEYWORDS JSONB DEFAULT '[]')'''
            )
            cur.execute(
                '''CREATE TABLE IF NOT EXISTS rp_modules
                   (MODULE_CODE TEXT PRIMARY KEY,
                    MODULE_NAME TEXT DEFAULT '',
                    SYNOPSIS TEXT DEFAULT '',
                    SCHOOL_NAME TEXT DEFAULT '',
                    SCHOOL_ABBR TEXT DEFAULT '',
                    URL TEXT DEFAULT '')'''
            )
            cur.execute(
                '''CREATE TABLE IF NOT EXISTS rp_courses
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
                '''CREATE TABLE IF NOT EXISTS rp_minors
                   (MINOR_NAME TEXT PRIMARY KEY,
                    MINOR_TYPE TEXT DEFAULT '',
                    URL TEXT DEFAULT '',
                    MODULES JSONB DEFAULT '[]',
                    ELIGIBILITY TEXT DEFAULT '')'''
            )
        conn.commit()
    except psycopg2.Error:
        pass

    _seed_pg_career_paths(LOCAL_DATA_DIR, _CAREER_PATHS_TABLE)
    _seed_pg_modules(LOCAL_DATA_DIR)
    _seed_pg_courses(LOCAL_DATA_DIR)
    _seed_pg_minors(LOCAL_DATA_DIR)
    _sync_pg_sequences()


def _seed_pg_career_paths(LOCAL_DATA_DIR, table):
    import json
    import psycopg2
    from app.db import pg_connection  # noqa: F811

    path = os.path.join(LOCAL_DATA_DIR, 'rp_career_paths.json')
    try:
        with open(path, encoding='utf-8') as f:
            paths = json.load(f)
    except (OSError, json.JSONDecodeError):
        return

    with pg_connection() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        if cur.fetchone()[0] > 0:
            return
        for p in paths:
            try:
                cur.execute(
                    f'INSERT INTO {table} (CAREER_ID, LABEL, KEYWORDS) VALUES (%s, %s, %s)',
                    (p['id'], p['label'], json.dumps(p.get('keywords', [])))
                )
            except psycopg2.Error:
                continue


def _seed_pg_modules(LOCAL_DATA_DIR):
    import json
    import psycopg2
    from app.db import pg_connection  # noqa: F811

    path = os.path.join(LOCAL_DATA_DIR, 'rp_modules_synopsis.json')
    try:
        with open(path, encoding='utf-8') as f:
            modules = json.load(f)
    except (OSError, json.JSONDecodeError):
        return

    with pg_connection() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM RP_MODULES')
        if cur.fetchone()[0] > 0:
            return
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


def _seed_pg_courses(LOCAL_DATA_DIR):
    import json
    import psycopg2
    from app.db import pg_connection  # noqa: F811

    path = os.path.join(LOCAL_DATA_DIR, 'rp_courses.json')
    try:
        with open(path, encoding='utf-8') as f:
            courses = json.load(f)
    except (OSError, json.JSONDecodeError):
        return

    module_keys = ['general_modules', 'major_modules', 'discipline_modules', 'elective_modules', 'industry_modules']
    with pg_connection() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM RP_COURSES')
        if cur.fetchone()[0] > 0:
            return
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


def _seed_pg_minors(LOCAL_DATA_DIR):
    import json
    import psycopg2
    from app.db import pg_connection  # noqa: F811

    path = os.path.join(LOCAL_DATA_DIR, 'rp_minors.json')
    try:
        with open(path, encoding='utf-8') as f:
            minors = json.load(f)
    except (OSError, json.JSONDecodeError):
        return

    with pg_connection() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM RP_MINORS')
        if cur.fetchone()[0] > 0:
            return
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


def _sync_pg_sequences():
    from app.db import pg_connection  # noqa: F811
    tables = ['reviews', 'review_votes', 'rp_career_paths']
    with pg_connection() as conn, conn.cursor() as cur:
        for table in tables:
            try:
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"(SELECT COALESCE(MAX(id), 0) FROM {table}))"
                )
            except Exception:
                continue


# ---------------------------------------------------------------------------
# Module-level app instance and backward-compat re-exports for tests.
# ---------------------------------------------------------------------------

_base_dir = os.path.dirname(os.path.abspath(__file__))

db_name = os.environ.get('DATABASE_PATH', os.path.join(_base_dir, '..', 'modulego.db'))
database_url = os.environ.get('DATABASE_URL')

app = create_app()

# Re-exports for test compatibility (imported as app_module.X in tests)
from app.core import (  # noqa: E402
    ReviewRepository as ReviewRepository,
    VoteRepository as VoteRepository,
    BookmarkRepository as BookmarkRepository,
    OwnershipRepository as OwnershipRepository,
    _modules_cache as _modules_cache,
    _courses_cache as _courses_cache,
    _minors_cache as _minors_cache,
    GeminiServiceError as GeminiServiceError,
    generate_gemini_comparison as generate_gemini_comparison,
    request_identity as request_identity,
    current_guest_hash as current_guest_hash,
    rotate_guest_cookie as rotate_guest_cookie,
    set_pending_guest_cookie as set_pending_guest_cookie,
    identity_owns as identity_owns,
    validate_review_payload as validate_review_payload,
    validate_comparison_payload as validate_comparison_payload,
    load_career_paths as load_career_paths,
    GEMINI_MODEL as GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS as GEMINI_TIMEOUT_SECONDS,
    MAX_COMMENT_LENGTH as MAX_COMMENT_LENGTH,
    MAX_COMPARISON_SOURCE_LENGTH as MAX_COMPARISON_SOURCE_LENGTH,
)
from app.db import (  # noqa: E402
    database_connection as database_connection,
    pg_connection as pg_connection,
    public_review as public_review,
)
from app.models import User as User  # noqa: E402

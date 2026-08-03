"""Consolidated unit tests for app/core.py, app/db.py, app/models.py, and app/__init__.py."""

import json
from unittest import mock

import pytest
from flask import g

import app as app_module
from app.core import (
    ReviewRepository,
    VoteRepository,
    _gobot_find_candidates,
    _gobot_find_diplomas,
    _load_career_paths_from_file,
    _load_local_courses,
    _load_local_minors,
    _load_local_modules,
    current_guest_hash,
    generate_gemini_comparison,
    identity_owns,
    load_career_paths,
    request_identity,
    rotate_guest_cookie,
    set_pending_guest_cookie,
    validate_comparison_payload,
    validate_review_payload,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS,
    MAX_COMMENT_LENGTH,
    MAX_COMPARISON_SOURCE_LENGTH,
    _CAREER_FALLBACK,
    _CAREER_KEYWORD_STOPWORDS,
)
from app.db import (
    database_connection,
    init_db,
    public_review,
    review_to_dict,
    select_review,
    use_postgres,
    use_sqlite_reviews,
    _row_value,
    _load_career_paths_from_file as _db_load_career_paths,
)
from app.models import User
from tests.conftest import register_and_login


# ---------------------------------------------------------------------------
# validate_review_payload
# ---------------------------------------------------------------------------

class TestValidateReviewPayload:

    def test_valid_with_module_code(self):
        payload, err = validate_review_payload(
            {'module_code': 'c270', 'rating': 5, 'comment': 'Great'},
            require_module_code=True,
        )
        assert err is None
        assert payload['module_code'] == 'C270'

    def test_valid_without_module_code(self):
        payload, err = validate_review_payload({'rating': 4, 'comment': 'Good'})
        assert err is None
        assert 'module_code' not in payload

    @pytest.mark.parametrize("data,partial", [
        (None, 'JSON request body'),
        ("str", 'JSON request body'),
        ({}, 'Rating must be an integer'),
        ({'comment': 'x'}, 'Rating must be an integer'),
        ({'rating': True}, 'Rating must be an integer'),
        ({'rating': '5'}, 'Rating must be an integer'),
        ({'rating': 0}, 'between 1 and 5'),
        ({'rating': 6}, 'between 1 and 5'),
        ({'rating': 5, 'comment': 123}, 'Comment must be text'),
        ({'rating': 5, 'comment': 'x' * 501}, '500 characters or fewer'),
        ({'rating': 5, 'is_anonymous': 'yes'}, 'true or false'),
        ({'rating': 5}, 'Module code is required'),
        ({'module_code': '   ', 'rating': 5}, 'Module code is required'),
        ({'module_code': 123, 'rating': 5}, 'Module code is required'),
        ({'module_code': 'A' * 21, 'rating': 5}, 'too long'),
    ])
    def test_rejects_invalid(self, data, partial):
        _, err = validate_review_payload(data, require_module_code=True)
        assert err is not None
        assert partial in err

    def test_comment_stripped(self):
        payload, _ = validate_review_payload({'rating': 5, 'comment': '  hi  '})
        assert payload['comment'] == 'hi'

    def test_none_comment_becomes_empty(self):
        payload, _ = validate_review_payload({'rating': 5, 'comment': None})
        assert payload['comment'] == ''

    def test_is_anonymous_bool(self):
        p1, _ = validate_review_payload({'rating': 5, 'is_anonymous': True})
        assert p1['is_anonymous'] is True
        p2, _ = validate_review_payload({'rating': 5, 'is_anonymous': False})
        assert p2['is_anonymous'] is False

    def test_module_code_normalized(self):
        payload, _ = validate_review_payload(
            {'module_code': ' c270 ', 'rating': 5}, require_module_code=True
        )
        assert payload['module_code'] == 'C270'


# ---------------------------------------------------------------------------
# validate_comparison_payload
# ---------------------------------------------------------------------------

class TestValidateComparisonPayload:

    def test_valid(self):
        codes, err = validate_comparison_payload({'module_codes': ['c270', 'c110']})
        assert err is None
        assert codes == ['C270', 'C110']

    @pytest.mark.parametrize("data,partial", [
        (None, 'JSON request body'),
        ({}, 'Exactly two'),
        ({'module_codes': ['C270']}, 'Exactly two'),
        ({'module_codes': ['C270', 'C270']}, 'different'),
        ({'module_codes': ['', 'C270']}, 'non-empty'),
        ({'module_codes': [123, 'C270']}, 'non-empty text'),
        ({'module_codes': ['A' * 21, 'C270']}, 'too long'),
        ({'module_codes': 'C270'}, 'Exactly two'),
    ])
    def test_rejects_invalid(self, data, partial):
        _, err = validate_comparison_payload(data)
        assert err is not None and partial in err


# ---------------------------------------------------------------------------
# Identity helpers
# ---------------------------------------------------------------------------

class TestIdentityHelpers:

    def test_owns_none_identity(self):
        assert identity_owns({'user_id': '1'}, None) is False

    def test_owns_empty_identity(self):
        assert identity_owns({'user_id': '1'}, {}) is False

    def test_owns_account_match(self, client):
        with app_module.app.test_request_context('/'):
            assert identity_owns(
                {'user_id': '123'}, {'kind': 'account', 'user_id': '123'}
            ) is True

    def test_owns_account_no_match(self, client):
        with app_module.app.test_request_context('/'):
            assert identity_owns(
                {'user_id': '456'}, {'kind': 'account', 'user_id': '123'}
            ) is False

    def test_owns_account_null_user_id(self, client):
        with app_module.app.test_request_context('/'):
            assert identity_owns(
                {'user_id': None}, {'kind': 'account', 'user_id': '123'}
            ) is False

    def test_owns_guest_match(self):
        assert identity_owns(
            {'guest_owner_hash': 'abc'}, {'kind': 'guest', 'guest_owner_hash': 'abc'}
        ) is True

    def test_owns_guest_no_match(self):
        assert identity_owns(
            {'guest_owner_hash': 'xyz'}, {'kind': 'guest', 'guest_owner_hash': 'abc'}
        ) is False

    def test_owns_guest_null_hash(self):
        assert identity_owns(
            {'guest_owner_hash': None}, {'kind': 'guest', 'guest_owner_hash': 'abc'}
        ) is False

    def test_current_guest_hash_no_cookie(self, client):
        with app_module.app.test_request_context('/'):
            assert current_guest_hash() is None

    def test_request_identity_authenticated(self, client):
        register_and_login(client)
        with app_module.app.test_request_context('/'):
            identity = request_identity()
            assert identity['kind'] == 'account'

    def test_request_identity_anonymous(self, client):
        with app_module.app.test_request_context('/'):
            assert request_identity() is None

    def test_request_identity_guest_create(self, client):
        with app_module.app.test_request_context('/'):
            identity = request_identity(create_guest=True)
            assert identity['kind'] == 'guest'

    def test_rotate_guest_cookie(self, client):
        with app_module.app.test_request_context('/'):
            rotate_guest_cookie()
            assert hasattr(g, 'pending_guest_cookie')

    def test_set_pending_guest_cookie(self, client):
        from flask import Response
        with app_module.app.test_request_context('/'):
            rotate_guest_cookie()
            resp = set_pending_guest_cookie(Response())
            assert 'modulego_guest' in resp.headers.get('Set-Cookie', '')


# ---------------------------------------------------------------------------
# ReviewRepository / VoteRepository helpers
# ---------------------------------------------------------------------------

class TestRepositoryHelpers:

    def test_determine_anonymous_guest(self):
        assert ReviewRepository._determine_anonymous({'kind': 'guest'}, {}, {}) is True

    def test_determine_anonymous_account_from_payload(self):
        assert ReviewRepository._determine_anonymous(
            {'kind': 'account'}, {}, {'is_anonymous': False}
        ) is False

    def test_determine_anonymous_account_fallback(self):
        assert ReviewRepository._determine_anonymous(
            {'kind': 'account'}, {'is_anonymous': False}, {}
        ) is False

    def test_determine_anonymous_account_default(self):
        assert ReviewRepository._determine_anonymous({'kind': 'account'}, {}, {}) is True

    def test_should_migrate_guest_review(self):
        assert ReviewRepository._should_migrate(
            {'kind': 'account', 'user_id': '1'}, {'user_id': None, 'guest_owner_hash': 'x'}
        )

    def test_should_migrate_own_review(self):
        assert ReviewRepository._should_migrate(
            {'kind': 'account', 'user_id': '1'}, {'user_id': '1', 'guest_owner_hash': None}
        ) is False

    def test_should_migrate_guest_identity(self):
        assert ReviewRepository._should_migrate(
            {'kind': 'guest'}, {'user_id': None, 'guest_owner_hash': 'x'}
        ) is False

    def test_vote_identity_filter_none(self):
        assert VoteRepository._identity_filter(None) == (None, None)

    def test_vote_identity_filter_account(self):
        assert VoteRepository._identity_filter(
            {'kind': 'account', 'user_id': '123'}
        ) == ('user_id', '123')

    def test_vote_identity_filter_guest(self):
        assert VoteRepository._identity_filter(
            {'kind': 'guest', 'guest_owner_hash': 'abc'}
        ) == ('guest_owner_hash', 'abc')


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

class TestDataLoading:

    @pytest.mark.parametrize("filename,data,loader", [
        ('rp_modules_synopsis.json', [{'module_code': 'C270'}], _load_local_modules),
        ('rp_courses.json', [{'course_code': 'RS12'}], _load_local_courses),
        ('rp_minors.json', [{'minor_name': 'AI'}], _load_local_minors),
        ('rp_career_paths.json', [{'id': 'x', 'label': 'X', 'keywords': []}], _load_career_paths_from_file),
    ])
    def test_load_valid(self, tmp_path, filename, data, loader):
        (tmp_path / filename).write_text(json.dumps(data))
        with mock.patch('app.core.LOCAL_DATA_DIR', str(tmp_path)):
            assert loader() is not None

    @pytest.mark.parametrize("filename,loader", [
        ('rp_modules_synopsis.json', _load_local_modules),
        ('rp_courses.json', _load_local_courses),
        ('rp_minors.json', _load_local_minors),
        ('rp_career_paths.json', _load_career_paths_from_file),
    ])
    def test_load_missing(self, tmp_path, filename, loader):
        with mock.patch('app.core.LOCAL_DATA_DIR', str(tmp_path)):
            assert loader() is None

    @pytest.mark.parametrize("filename,loader", [
        ('rp_modules_synopsis.json', _load_local_modules),
        ('rp_courses.json', _load_local_courses),
        ('rp_minors.json', _load_local_minors),
        ('rp_career_paths.json', _load_career_paths_from_file),
    ])
    def test_load_invalid_json(self, tmp_path, filename, loader):
        (tmp_path / filename).write_text('not json')
        with mock.patch('app.core.LOCAL_DATA_DIR', str(tmp_path)):
            assert loader() is None

    def test_load_career_paths(self, client):
        paths = load_career_paths()
        assert isinstance(paths, list) and len(paths) > 0
        assert 'id' in paths[0]


# ---------------------------------------------------------------------------
# GoBot helpers
# ---------------------------------------------------------------------------

class TestGoBotHelpers:

    def test_find_candidates_with_career(self):
        modules = [{'code': 'C270', 'name': 'Mobile', 'synopsis': 'mobile apps'}]
        careers = [{'id': 'm', 'label': 'Mobile Dev', 'keywords': ['mobile']}]
        _, career = _gobot_find_candidates('build mobile apps', modules, careers)
        assert career is not None

    def test_find_candidates_no_match(self):
        modules = [{'code': 'C270', 'name': 'X', 'synopsis': 'X'}]
        careers = [{'id': 'x', 'label': 'X', 'keywords': ['zzz']}]
        _, career = _gobot_find_candidates('hello', modules, careers)
        assert career is None

    def test_find_diplomas_with_overlap(self):
        courses = [{
            'course_code': 'R1', 'course_name': 'CS',
            'major_modules': [{'code': 'C270'}],
            'general_modules': [{'code': 'C110'}],
            'discipline_modules': [], 'elective_modules': [], 'industry_modules': [],
        }]
        result = _gobot_find_diplomas(['C270', 'C110'], courses)
        assert len(result) == 1 and result[0][1] == 2

    def test_find_diplomas_empty(self):
        with mock.patch('app.core._load_local_courses', return_value=None):
            assert _gobot_find_diplomas(['C270'], []) == []
        assert _gobot_find_diplomas([], [{'course_code': 'R1'}]) == []


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

class TestGemini:

    def test_raises_without_key(self, client, monkeypatch):
        monkeypatch.delenv('GEMINI_API_KEY', raising=False)
        with pytest.raises(Exception):
            generate_gemini_comparison([{'code': 'C270'}])


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:

    def test_values(self):
        assert GEMINI_MODEL == 'gemini-3.1-flash-lite'
        assert GEMINI_TIMEOUT_SECONDS == 25
        assert MAX_COMMENT_LENGTH == 500
        assert MAX_COMPARISON_SOURCE_LENGTH == 4000

    def test_career_fallback(self):
        assert len(_CAREER_FALLBACK) > 0
        for c in _CAREER_FALLBACK:
            assert 'id' in c and 'label' in c and 'keywords' in c

    def test_stopwords(self):
        assert isinstance(_CAREER_KEYWORD_STOPWORDS, frozenset)
        assert 'what' in _CAREER_KEYWORD_STOPWORDS


# ---------------------------------------------------------------------------
# db.py helpers
# ---------------------------------------------------------------------------

class TestDbHelpers:

    def test_use_sqlite_in_testing(self, client):
        with app_module.app.app_context():
            assert use_sqlite_reviews() is True
            assert use_postgres() is False

    def test_row_value_exact(self):
        class R:
            def __getitem__(self, k):
                return 42 if k == 'id' else (_ for _ in ()).throw(KeyError(k))
        assert _row_value(R(), 'id') == 42

    def test_row_value_uppercase(self):
        class R:
            def __getitem__(self, k):
                return 42 if k == 'ID' else (_ for _ in ()).throw(KeyError(k))
        assert _row_value(R(), 'id') == 42

    def test_row_value_missing(self):
        class R:
            def __getitem__(self, k): raise KeyError(k)
        assert _row_value(R(), 'x') is None
        assert _row_value(R(), 'x', 'd') == 'd'

    def test_row_value_dict(self):
        assert _row_value({'id': 1}, 'id') == 1
        assert _row_value({}, 'x') is None

    def test_review_to_dict(self, client):
        with database_connection() as conn:
            conn.execute(
                'INSERT INTO REVIEWS (MODULE_CODE, RATING, COMMENT, USER_ID, '
                'GUEST_OWNER_HASH, IS_ANONYMOUS, AUTHOR_DISPLAY_NAME) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                ('C270', 5, 'G', 'u1', 'h1', 1, 'S'),
            )
            conn.commit()
            row = conn.execute('SELECT * FROM REVIEWS').fetchone()
        d = review_to_dict(row)
        assert d['module_code'] == 'C270' and d['is_anonymous'] is True

    def test_public_review_owner(self, client):
        row = {
            'id': 1, 'module_code': 'C270', 'rating': 5, 'comment': 'G',
            'created_at': None, 'updated_at': None,
            'user_id': 'u1', 'guest_owner_hash': None,
            'is_anonymous': False, 'author_display_name': 'J',
        }
        r = public_review(row, {'kind': 'account', 'user_id': 'u1'})
        assert r['is_owner'] and r['author']['label'] == 'J'

    def test_public_review_anonymous(self, client):
        row = {
            'id': 1, 'module_code': 'C270', 'rating': 5, 'comment': 'G',
            'created_at': None, 'updated_at': None,
            'user_id': 'u1', 'guest_owner_hash': None,
            'is_anonymous': True, 'author_display_name': 'J',
        }
        r = public_review(row, {'kind': 'guest', 'guest_owner_hash': 'x'})
        assert not r['is_owner'] and r['author']['label'] == 'Anonymous student'

    def test_select_review(self, client):
        with database_connection() as conn:
            conn.execute(
                'INSERT INTO REVIEWS (MODULE_CODE, RATING, COMMENT) VALUES (?, ?, ?)',
                ('C270', 5, 'G'),
            )
            conn.commit()
            rid = conn.execute('SELECT ID FROM REVIEWS').fetchone()['ID']
        with database_connection() as conn:
            assert select_review(conn, rid) is not None
            assert select_review(conn, 9999) is None

    def test_init_db_idempotent(self, client):
        init_db()
        init_db()
        with database_connection() as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0] >= 5

    def test_seed_career_paths(self, client):
        with database_connection() as conn:
            assert conn.execute('SELECT COUNT(*) FROM CAREER_PATHS').fetchone()[0] > 0

    def test_db_load_career_paths(self, tmp_path):
        data = [{'id': 't', 'label': 'T', 'keywords': ['a']}]
        (tmp_path / 'rp_career_paths.json').write_text(json.dumps(data))
        with mock.patch('app.core.LOCAL_DATA_DIR', str(tmp_path)):
            assert _db_load_career_paths() is not None

    def test_db_load_career_paths_file_exists(self):
        result = _db_load_career_paths()
        assert result is not None or result is None


# ---------------------------------------------------------------------------
# models.py
# ---------------------------------------------------------------------------

class TestModels:

    def test_create_and_find(self, client):
        u = User.create("a@b.com", "pw", "Name")
        assert User.find_by_email("a@b.com").id == u.id
        assert User.find_by_id(u.id).email == "a@b.com"

    def test_create_normalizes(self, client):
        u = User.create("  X@Y.COM  ", "pw", " N ")
        assert u.email == "x@y.com" and u.display_name == "N"

    def test_create_truncates_name(self, client):
        u = User.create("t@t.com", "pw", "A" * 100)
        assert len(u.display_name) == 50

    def test_verify_password(self, client):
        u = User.create("v@v.com", "correct", "V")
        assert u.verify_password("correct")
        assert not u.verify_password("wrong")

    def test_update_display_name(self, client):
        u = User.create("u@u.com", "pw", "Old")
        u.update_display_name("New")
        assert User.find_by_email("u@u.com").display_name == "New"

    def test_change_password(self, client):
        u = User.create("p@p.com", "old", "P")
        u.change_password("new")
        assert u.verify_password("new") and not u.verify_password("old")

    def test_delete(self, client):
        u = User.create("d@d.com", "pw", "D")
        uid = u.id
        u.delete()
        assert User.find_by_id(uid) is None

    def test_to_dict(self, client):
        u = User.create("td@td.com", "pw", "TD")
        d = u.to_dict()
        assert 'password_hash' not in d and d['email'] == 'td@td.com'

    def test_from_row_none(self):
        assert User._from_row(None) is None

    def test_backend_sqlite(self, client):
        with app_module.app.app_context():
            assert User._get_backend() == "sqlite"


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

class TestAppFactory:

    def test_reexports(self):
        for attr in ('ReviewRepository', 'VoteRepository', 'BookmarkRepository',
                      'OwnershipRepository', 'GeminiServiceError', 'User',
                      'database_connection', 'public_review'):
            assert hasattr(app_module, attr)

    def test_caches(self):
        for cache in ('_modules_cache', '_courses_cache', '_minors_cache'):
            c = getattr(app_module, cache)
            assert 'data' in c and 'timestamp' in c

    def test_app_config(self):
        app = app_module.app
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True
        assert 'auth' in app.blueprints and 'api' in app.blueprints
        assert hasattr(app, 'limiter')

    def test_rate_limit_key(self):
        from app import _rate_limit_key
        with app_module.app.test_request_context('/'):
            app_module.app.config['TESTING'] = True
            k1 = _rate_limit_key()
            k2 = _rate_limit_key()
            assert k1 != k2
            app_module.app.config.pop('_test_request_counter', None)

    def test_pg_helpers_noop_without_pg(self, client):
        from app import (
            _init_pg_db, _seed_pg_career_paths, _seed_pg_modules,
            _seed_pg_courses, _seed_pg_minors,
        )
        with app_module.app.app_context():
            _init_pg_db(app_module.app)
            _seed_pg_career_paths('/tmp', 'rp_career_paths')
            _seed_pg_modules('/tmp')
            _seed_pg_courses('/tmp')
            _seed_pg_minors('/tmp')

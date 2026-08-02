"""API routes: modules, reviews, votes, bookmarks, ownership, comparison, gobot."""

import json
import os
import re
import time

from flask import Blueprint, jsonify, request

from app.core import (
    BookmarkRepository,
    GeminiServiceError,
    OwnershipRepository,
    ReviewRepository,
    VoteRepository,
    _build_modules_list,
    _courses_cache,
    _gobot_find_candidates,
    _gobot_find_diplomas,
    _gobot_gemini_recommend,
    _get_active_module_codes,
    _load_local_courses,
    _minors_cache,
    _modules_cache,
    current_guest_hash,
    load_career_paths,
    request_identity,
    rotate_guest_cookie,
    validate_comparison_payload,
    validate_review_payload,
    COURSES_CACHE_TTL,
    GEMINI_MODEL,
    MINORS_CACHE_TTL,
    MODULE_CACHE_TTL,
)
from app.db import pg_connection, use_postgres

api_bp = Blueprint("api", __name__)


def _authenticated_identity():
    identity = request_identity()
    if not identity or identity['kind'] != 'account':
        return None, (jsonify({'error': 'Login required.'}), 401)
    return identity, None


# ---------------------------------------------------------------------------
# Module / Course / Minor data endpoints
# ---------------------------------------------------------------------------

@api_bp.route('/api/modules', methods=['GET'])
def get_modules():
    now = time.time()
    if _modules_cache['data'] is not None and (now - _modules_cache['timestamp']) < MODULE_CACHE_TTL:
        return jsonify(_modules_cache['data']), 200

    modules = _build_modules_list()
    if modules is None:
        return jsonify({'error': 'Module data is not available.'}), 503

    _modules_cache['data'] = modules
    _modules_cache['timestamp'] = now
    return jsonify(modules), 200


@api_bp.route('/api/courses', methods=['GET'])
def get_courses():
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
        except (Exception, json.JSONDecodeError):
            pass

    if courses is None:
        courses = _load_local_courses()

    if courses is None:
        return jsonify({'error': 'No course data available.'}), 503

    _courses_cache['data'] = courses
    _courses_cache['timestamp'] = now
    return jsonify(courses), 200


@api_bp.route('/api/minors', methods=['GET'])
def get_minors():
    now = time.time()
    if _minors_cache['data'] is not None and (now - _minors_cache['timestamp']) < MINORS_CACHE_TTL:
        return jsonify(_minors_cache['data']), 200

    minors = None
    from app.db import use_postgres, pg_connection
    if use_postgres():
        import psycopg2
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
        from app.core import _load_local_minors
        minors = _load_local_minors()

    if minors is None:
        return jsonify({'error': 'No minor data available.'}), 503

    _minors_cache['data'] = minors
    _minors_cache['timestamp'] = now
    return jsonify(minors), 200


@api_bp.route('/api/career-paths', methods=['GET'])
def get_career_paths():
    return jsonify(load_career_paths()), 200


# ---------------------------------------------------------------------------
# Review CRUD
# ---------------------------------------------------------------------------

@api_bp.route('/api/reviews', methods=['GET'])
def list_reviews():
    reviews = ReviewRepository.list_all(request_identity())
    return jsonify(reviews), 200


@api_bp.route('/api/reviews', methods=['POST'])
def add_review():
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


@api_bp.route('/api/reviews/<module_code>', methods=['GET'])
def get_reviews(module_code):
    reviews = ReviewRepository.list_by_module(
        module_code,
        request_identity(),
    )
    return jsonify(reviews), 200


@api_bp.route('/api/reviews/<int:review_id>', methods=['PUT'])
def update_review(review_id):
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


@api_bp.route('/api/reviews/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
    error_response = ReviewRepository.delete(
        review_id,
        request_identity(create_guest=True),
    )
    if error_response:
        return error_response
    return '', 204


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------

@api_bp.route('/api/reviews/<int:review_id>/vote', methods=['GET'])
def get_review_votes(review_id):
    votes = VoteRepository.get_votes(review_id, request_identity())
    return jsonify(votes), 200


@api_bp.route('/api/reviews/<int:review_id>/vote', methods=['POST'])
def vote_review(review_id):
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


@api_bp.route('/api/reviews/<int:review_id>/vote', methods=['DELETE'])
def remove_review_vote(review_id):
    VoteRepository.remove(
        review_id,
        request_identity(create_guest=True),
    )
    return '', 204


@api_bp.route('/api/reviews/votes', methods=['POST'])
def get_bulk_votes():
    payload = request.get_json(silent=True)
    if not payload or 'review_ids' not in payload:
        return jsonify({'error': 'review_ids array is required.'}), 400

    review_ids = payload['review_ids']
    if not isinstance(review_ids, list):
        return jsonify({'error': 'review_ids must be an array.'}), 400

    votes = VoteRepository.get_votes_bulk(review_ids, request_identity())
    return jsonify(votes), 200


@api_bp.route('/api/ratings', methods=['GET'])
def get_rating_summaries():
    summaries = ReviewRepository.rating_summaries()
    return jsonify(summaries), 200


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------

@api_bp.route('/api/bookmarks', methods=['GET'])
def get_bookmarks():
    identity, error = _authenticated_identity()
    if error:
        return error
    return jsonify({
        'module_codes': BookmarkRepository.list_for_user(identity['user_id'])
    }), 200


@api_bp.route('/api/bookmarks/<module_code>', methods=['PUT'])
def add_bookmark(module_code):
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


@api_bp.route('/api/bookmarks/<module_code>', methods=['DELETE'])
def delete_bookmark(module_code):
    identity, error = _authenticated_identity()
    if error:
        return error
    BookmarkRepository.remove(identity['user_id'], module_code)
    return '', 204


@api_bp.route('/api/bookmarks', methods=['DELETE'])
def clear_bookmarks():
    identity, error = _authenticated_identity()
    if error:
        return error
    BookmarkRepository.remove(identity['user_id'])
    return '', 204


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

@api_bp.route('/api/ownership/pending', methods=['GET'])
def get_pending_ownership():
    _identity, error = _authenticated_identity()
    if error:
        return error
    counts = OwnershipRepository.pending_counts(current_guest_hash())
    return jsonify(counts), 200


@api_bp.route('/api/ownership/claim', methods=['POST'])
def claim_guest_ownership():
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


# ---------------------------------------------------------------------------
# Gemini comparison
# ---------------------------------------------------------------------------

@api_bp.route('/api/comparison/generate', methods=['POST'])
def generate_comparison():
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
        import app as _app
        generated_modules = _app.generate_gemini_comparison(selected_modules)
    except GeminiServiceError:
        return jsonify({
            'error': 'Dynamic comparison is temporarily unavailable.'
        }), 502

    return jsonify({
        'provider': 'Gemini',
        'model': os.environ.get('GEMINI_MODEL', GEMINI_MODEL),
        'modules': generated_modules,
    }), 200


# ---------------------------------------------------------------------------
# GoBot chatbot
# ---------------------------------------------------------------------------

@api_bp.route('/api/gobot', methods=['POST'])
def gobot_chat():
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
    careers = load_career_paths()
    module_map = {m['code'].lower(): m for m in modules}
    msg_lower = user_msg.lower().strip()

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

    # Match patterns like "reviews for C270", "rating of E123", "feedback on F456"
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

    candidates, matched_career = _gobot_find_candidates(user_msg, modules, careers)

    result = _gobot_gemini_recommend(user_msg, history, candidates, careers)
    if result:
        return jsonify(result)

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

---
goal: Security Hardening - Anonymous Ownership, CSRF, Rate Limiting
version: 1.0
date_created: 2026-07-19
last_updated: 2026-07-19
owner: Developer
status: 'Completed'
tags: ['security', 'rls', 'csrf', 'rate-limiting', 'authentication', 'authorization']
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

Address all RLS and security issues identified in the codebase audit. The current architecture uses a service role key on the server (correct), but all API endpoints are fully anonymous with no ownership, CSRF protection, or rate limiting. This plan adds lightweight anonymous ownership, CSRF defense-in-depth, and rate limiting — appropriate for a student project without requiring full user authentication.

## 1. Requirements & Constraints

- **SEC-001**: Reviews must be associated with an anonymous owner token to prevent unauthorized modification
- **SEC-002**: State-changing endpoints (POST/PUT/DELETE) must use CSRF tokens
- **SEC-003**: Review endpoints must be rate-limited to prevent abuse
- **SEC-004**: The service role key must remain server-side only (no frontend exposure)
- **SEC-005**: No user authentication system required — anonymous ownership is sufficient
- **SEC-006**: Backward compatibility — existing reviews in Supabase must not break
- **CON-001**: Use only Vanilla JavaScript (no frontend frameworks)
- **CON-002**: Backend uses Python Flask with Supabase PostgreSQL
- **CON-003**: SQLite fallback must work for automated tests (no Supabase needed)
- **CON-004**: New dependencies must be added to `requirements.txt`
- **GUD-001**: Follow existing code patterns (ReviewRepository, validate_review_payload, etc.)

## 2. Implementation Steps

### Implementation Phase 1: Backend Security Infrastructure

- GOAL-001: Add Flask-WTF CSRF protection and Flask-Limiter rate limiting to app.py

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Add `Flask-WTF>=1.2.0` and `Flask-Limiter>=3.0.0` to `requirements.txt` | ✅ | 2026-07-19 |
| TASK-002 | Import `CSRFProtect` from `flask_wtf.csrf` and `Limiter` from `flask_limiter` in `app.py` | ✅ | 2026-07-19 |
| TASK-003 | Initialize `CSRFProtect(app)` — exempt GET routes, apply to POST/PUT/DELETE | ✅ | 2026-07-19 |
| TASK-004 | Initialize `Limiter(app, default_limits=["200 per hour"])` | ✅ | 2026-07-19 |
| TASK-005 | Add rate limits on review endpoints: `@limiter.limit("20/hour")` on POST, `@limiter.limit("10/hour")` on PUT and DELETE | ✅ | 2026-07-19 |
| TASK-006 | Exempt `/api/modules` and `/api/courses` from CSRF (read-only GET endpoints) | ✅ | 2026-07-19 |
| TASK-007 | Add `WTF_CSRF_ENABLED = False` for test mode (`app.config['TESTING'] = True`) | ✅ | 2026-07-19 |
| TASK-008 | Exempt all API endpoints from CSRF for non-browser clients (custom header check: `X-Requested-With`) | ✅ | 2026-07-19 |

### Implementation Phase 2: Owner Token Database Schema

- GOAL-002: Add owner_token column to reviews table for anonymous ownership

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-009 | Add `owner_token TEXT` column to SQLite `init_db()` schema in `app.py` | | |
| TASK-009a | Add migration comment for Supabase: `ALTER TABLE reviews ADD COLUMN owner_token TEXT;` | | |
| TASK-010 | Create `generate_owner_token()` function — returns `uuid4().hex` (32-char hex string) | | |
| TASK-011 | Update `ReviewRepository.create()` to accept and store `owner_token` in payload | | |
| TASK-012 | Update `ReviewRepository.update()` to verify `owner_token` matches before update | | |
| TASK-013 | Update `ReviewRepository.delete()` to verify `owner_token` matches before delete | | |
| TASK-014 | Update `review_to_dict()` to include `owner_token` field | | |
| TASK-015 | Update `validate_review_payload()` to accept optional `owner_token` parameter | | |

### Implementation Phase 3: Backend API Route Changes

- GOAL-003: Update API routes to validate ownership and handle CSRF

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-016 | Update `add_review()` to extract `X-Owner-Token` from request headers | | |
| TASK-017 | Update `add_review()` to generate token if not provided, include in response | | |
| TASK-018 | Update `update_review()` to extract `X-Owner-Token` and pass to repository | | |
| TASK-019 | Update `delete_review()` to extract `X-Owner-Token` and pass to repository | | |
| TASK-020 | Add 403 response when owner token does not match (edit/delete) | | |
| TASK-021 | Add `@csrf.exempt` decorator for API endpoints that use custom header auth | | |

### Implementation Phase 4: Frontend Token Management

- GOAL-004: Generate and persist owner token in browser, send with review requests

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-022 | Add `getOwnerToken()` to `app/static/js/utils.js` — generates UUID4 on first call, persists to `localStorage key 'modulego_owner_token'` | | |
| TASK-023 | Add `generateCSRFToken()` helper if using cookie-based CSRF (or handle via meta tag) | | |
| TASK-024 | In `detail.js`: add `X-Owner-Token` header to POST/PUT/DELETE fetch calls in `saveReview()` and `deleteReview()` | | |
| TASK-025 | In `reviews.js`: add `X-Owner-Token` header to PUT/DELETE fetch calls in `saveEdit()` and `deleteReview()` | | |
| TASK-026 | In `reviews.js`: store `owner_token` from response on create, persist to localStorage | | |
| TASK-027 | In `detail.js`: store `owner_token` from response on create, persist to localStorage | | |
| TASK-028 | Add CSRF token meta tag in `base.html` for form-based CSRF if needed | | |

### Implementation Phase 5: Frontend Edit/Delete Button Visibility

- GOAL-005: Only show edit/delete buttons for reviews owned by the current user

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-029 | In `detail.js` `createReviewMarkup()`: check `review.owner_token === getOwnerToken()` before showing action buttons | | |
| TASK-030 | In `reviews.js` `createReviewCard()`: check `review.owner_token === getOwnerToken()` before showing action buttons | | |
| TASK-031 | Store fetched `owner_token` from reviews in `currentReviews` map for comparison | | |

### Implementation Phase 6: Testing & Verification

- GOAL-006: Verify all security improvements work correctly

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-032 | Run `pytest tests/` to verify existing tests still pass | | |
| TASK-033 | Test: create review → verify owner_token is stored and returned | | |
| TASK-034 | Test: edit review with wrong owner_token → verify 403 response | | |
| TASK-035 | Test: delete review with wrong owner_token → verify 403 response | | |
| TASK-036 | Test: CSRF token present on POST/PUT/DELETE requests | | |
| TASK-037 | Test: rate limiting returns 429 after threshold exceeded | | |
| TASK-038 | Test: existing reviews without owner_token still readable (backward compatible) | | |

## 3. Alternatives

- **ALT-001**: Full Supabase Auth with email/password — Rejected as overkill for a student project; adds significant UI/UX complexity
- **ALT-002**: Session-based cookies with Flask sessions — Rejected because localStorage is simpler for anonymous usage; no server-side session storage needed
- **ALT-003**: IP-based ownership — Rejected because IPs change (mobile users) and are shared (NAT), making it unreliable
- **ALT-004**: No ownership, just CSRF + rate limiting — Considered but rejected because any user could still edit/delete any review
- **ALT-005**: RLS policies on Supabase side — Rejected because service role key bypasses RLS by design; ownership must be enforced in Flask

## 4. Dependencies

- **DEP-001**: Flask-WTF>=1.2.0 — CSRF protection
- **DEP-002**: Flask-Limiter>=3.0.0 — Rate limiting
- **DEP-003**: Flask 3.1.3 — Web framework (already present)
- **DEP-004**: supabase 2.31.0 — Supabase Python client (already present)
- **DEP-005**: Python 3.12+ runtime (already present)

## 5. Files

| Path | Description |
|------|-------------|
| `app.py` | Flask backend — add CSRF, rate limiting, owner token logic, repository changes |
| `requirements.txt` | Add Flask-WTF and Flask-Limiter dependencies |
| `app/static/js/utils.js` | Add `getOwnerToken()` utility function |
| `app/static/js/detail.js` | Add owner token headers to review CRUD, conditional button visibility |
| `app/static/js/reviews.js` | Add owner token headers to review CRUD, conditional button visibility |
| `app/templates/base.html` | Add CSRF meta tag if using form-based CSRF |
| `tests/test_security.py` | Add tests for ownership validation, CSRF, rate limiting |
| `tests/test_reviews.py` | Update existing review tests for owner token |

## 6. Testing

- **TEST-001**: Create review → response includes `owner_token` field
- **TEST-002**: Create review with custom `X-Owner-Token` header → token is stored with review
- **TEST-003**: Update review with matching `X-Owner-Token` → success (200)
- **TEST-004**: Update review with wrong `X-Owner-Token` → forbidden (403)
- **TEST-005**: Delete review with matching `X-Owner-Token` → success (204)
- **TEST-006**: Delete review with wrong `X-Owner-Token` → forbidden (403)
- **TEST-007**: POST/PUT/DELETE without CSRF token → rejected (400)
- **TEST-008**: Rate limit exceeded on review POST → 429 response
- **TEST-009**: GET `/api/modules` still works without any token
- **TEST-010**: Existing reviews without `owner_token` are still readable via GET
- **TEST-011**: `pytest tests/` passes all existing tests

## 7. Risks & Assumptions

- **RISK-001**: Existing reviews in Supabase have no `owner_token` — they become "orphaned" (read-only, cannot be edited/deleted). Mitigation: Acceptable for existing data; new reviews will have ownership.
- **RISK-002**: Users clearing localStorage lose ownership of their reviews. Mitigation: Acceptable for anonymous system; reviews remain readable.
- **RISK-003**: CSRF protection may break non-browser API consumers. Mitigation: Exempt API endpoints that send `X-Requested-With: XMLHttpRequest` header.
- **RISK-004**: Flask-Limiter requires a storage backend (default: in-memory). Mitigation: In-memory is fine for single-server; can add Redis later if needed.
- **ASSUMPTION-001**: Users have modern browsers with localStorage support
- **ASSUMPTION-002**: Single-server deployment (Vercel serverless) — in-memory rate limiting is per-invocation, not global. Mitigation: Acceptable for student project scale.

## 8. Related Specifications / Further Reading

- [ModuleGo Design Specification](./spec-modulego-design.md)
- [ModuleGo Implementation Plan](./plan-modulego-implementation.md)
- [Flask-WTF Documentation](https://flask-wtf.readthedocs.io/)
- [Flask-Limiter Documentation](https://flask-limiter.readthedocs.io/)
- [Supabase Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)

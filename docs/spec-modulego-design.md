---
title: ModuleGo - Republic Polytechnic Module Viewer Design Specification
version: 9.0
date_created: 2026-06-29
last_updated: 2026-07-29
owner: Developer
status: 'In Progress'
tags: ['design', 'frontend', 'backend', 'vanilla-js', 'tailwindcss', 'glassmorphism', 'flask', 'supabase', 'ui-redesign', 'reviews', 'voting', 'minors', 'career-paths', 'gobot', 'bookmarks', 'share']
---

# Introduction

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

ModuleGo is a responsive web application that allows Republic Polytechnic students to search for modules, view module details, discover which diplomas offer each module, compare modules side-by-side, and leave reviews. The application addresses the limitation of the official RP Module viewer by providing a more intuitive and comprehensive module exploration experience.

## 1. Purpose & Scope

**Purpose:** Define the design system, UI components, and interaction patterns for the ModuleGo application, including the Tailwind CSS-based glassmorphism design system.

**Scope:** Full-stack web application with:
- Frontend: Vanilla JS, Tailwind CSS (glassmorphism), and HTML
- Backend: Python Flask server with Supabase PostgreSQL (modules, courses, minors, reviews, career paths)
- API endpoints for module data, review management, voting, career paths, GoBot chatbot, bookmarks, and sharing

**Audience:** Republic Polytechnic students seeking to explore modules and their associated diplomas.

**Assumptions:**
- Module data is stored in Supabase `rp_modules` table and served via `/api/modules`
- Course (diploma) data is served via `app/static/local-data/scripts/step3_scrape_diplomas.py` → Supabase `rp_courses` → `/api/courses`
- Minor programme data is served via `app/static/local-data/scripts/step4_scrape_minors.py` → Supabase → `/api/minors`
- Career path data is served via `app/static/local-data/scripts/step5_generate_career_paths.py` → Supabase → `/api/career-paths`
- Review data (ratings and comments) is stored in Supabase `reviews` table
- Review votes are stored in Supabase `review_votes` table
- Backend server runs on Python Flask and proxies all Supabase calls
- SQLite is used only for automated tests
- GoBot chatbot uses Gemini API for AI-assisted module recommendations
- Bookmarks and share functionality are client-side (localStorage)

## 2. Definitions

| Term | Definition |
|------|------------|
| Module | A course unit offered at Republic Polytechnic, identified by a module code (e.g., A001) |
| Diploma | A full-time program of study at RP (e.g., Diploma in Applied AI & Analytics) |
| School | Academic division at RP (e.g., School of Infocomm) |
| Client-side filtering | Searching/filtering data in the browser without server requests |
| Glassmorphism | A UI design trend using translucent backgrounds with blur and border effects |
| Tailwind CSS | A utility-first CSS framework used for styling the application |

## 3. Requirements, Constraints & Guidelines

### Core Requirements

- **REQ-001**: User can enter a search query into an input field
- **REQ-002**: User can submit the query (via pressing Enter)
- **REQ-003**: Search filters modules by Module Code, Module Name, Description, Category, or School
- **REQ-004**: Search results display as a list showing Module Code, Module Name, Description, Category, and School
- **REQ-005**: Clicking a module displays a list of diplomas offering that module
- **REQ-006**: Each module entry includes a link to the external RP module page (url field)
- **REQ-007**: User can filter modules by School using collapsible filter panel
- **REQ-008**: User can compare two modules side-by-side
- **REQ-009**: User can leave reviews with ratings (1-5) and comments on modules
- **REQ-010**: Reviews are stored in Supabase `reviews` table
- **REQ-011**: User can view existing reviews for each module
- **REQ-012**: User can filter by diploma (populated from `/api/courses`)
- **REQ-013**: User can filter by minimum average rating (5 Stars, 4 Stars & Up, etc.)
- **REQ-014**: User can toggle "Active" filter (modules appearing in at least one diploma)
- **REQ-015**: Filter state persisted in URL params (`q`, `school`, `diploma`, `rating`, `active`, `page`)
- **REQ-016**: Module details show a five-to-one-star rating distribution calculated from backend review data

### Bonus Requirements

- **REQ-B01**: Responsive design works on desktop, tablet, and mobile viewports
- **REQ-B02**: Loading animation displayed during initial data load
- **REQ-B03**: Module comparison page with side-by-side table view
- **REQ-B04**: Collapsible filter panel for school, diploma, rating, and active filters

### Review Voting Requirements

- **REQ-V01**: Users can upvote or downvote any review (except their own)
- **REQ-V02**: Each user can only vote once per review (changing vote replaces previous)
- **REQ-V03**: Vote buttons show current user's vote state (filled icon if voted)
- **REQ-V04**: Vote score (net upvotes minus downvotes) displayed next to buttons
- **REQ-V05**: Votes stored in Supabase (production) and SQLite (tests)
- **REQ-V06**: Review owner cannot vote on their own review

### GoBot Chatbot Requirements

- **REQ-G01**: "hi", "hello", "hey" → friendly greeting, no module data lookup
- **REQ-G02**: "thanks", "ok", "okay" → friendly acknowledgment
- **REQ-G03**: Module code "C270" → show module details
- **REQ-G04**: "C270???" (punctuation) → still match module C270
- **REQ-G05**: "python" → search modules (single-term search works)
- **REQ-G06**: "biology" → search modules (unknown career word still searches)
- **REQ-G07**: "reviews for C270" → show real reviews from DB
- **REQ-G08**: "C270 reviews" → same
- **REQ-G09**: "data analyst" → career-matched modules
- **REQ-G10**: Nonsense like "asdfghjkl" → fallback help, not fake results
- **REQ-G11**: Very short input "a", "?" → friendly nudge
- **CON-G01**: Zero hardcoded word lists (no stop words, no greeting lists)
- **CON-G02**: All heuristics must use length, position, or data-driven checks
- **CON-G03**: Punctuation stripped from tokens before matching against module data
- **CON-G04**: Exact module code matches ranked above text matches
- **GUD-G01**: Everything on the `gobot_chat` function in `app.py` — no new files
- **GUD-G02**: Handler order must be intentional — most specific first, fallback last
- **GUD-G03**: Each handler returns early — no else chains, no flags

### Bookmark & Share Requirements

- **REQ-BS01**: Users can bookmark/favorite modules (persisted in localStorage)
- **REQ-BS02**: Bookmarked modules are highlighted in search results
- **REQ-BS03**: Users can share module links via clipboard copy
- **REQ-BS04**: Users can export module data as CSV

### Constraints

- **CON-001**: Use only Vanilla JavaScript (no frameworks like React, Vue, Angular)
- **CON-002**: Use Tailwind CSS for styling (via CDN) with glassmorphism design tokens
- **CON-003**: Use HTML5 semantic elements
- **CON-004**: Backend uses Python Flask with Supabase PostgreSQL
- **CON-005**: Module data is stored in Supabase, diploma data is served via `/api/courses`
- **CON-006**: Project follows Flask app structure: `app/templates/` for HTML, `app/static/` for assets
- **CON-007**: Frontend never calls Supabase directly; all requests go through Flask API
- **CON-008**: Custom modal implementation replaces Bootstrap Modal (no Bootstrap JS dependency)

### Design Guidelines

- **GUD-001**: Follow RP brand colors with modern emerald palette: Primary (#00A651 mapped to emerald-500)
- **GUD-002**: Use Tailwind CSS utility classes for layout and responsive design (mobile-first)
- **GUD-003**: Maintain WCAG AA contrast ratios for accessibility
- **GUD-004**: Mobile-first responsive approach using Tailwind breakpoints (sm, md, lg, xl)
- **GUD-005**: Clean, functional UI with glassmorphism effects on navbar only; cards and surfaces go solid
- **GUD-006**: Use Inter font family for body, Outfit font family for display headings
- **GUD-007**: Clean minimal hero sections matching SaaS landing page patterns
- **GUD-008**: Solid cards with `shadow-sm`, hover elevates to `shadow-xl` — no backdrop-blur on cards
- **GUD-009**: Smooth transitions using `transition-all duration-300 ease-out` pattern
- **GUD-010**: Dark mode with `darkMode: 'class'` strategy — three modes: Light, Dark, System (follows OS preference)
- **GUD-011**: FOUC prevention via inline script in `<head>` that applies theme before body renders

## 4. Interfaces & Data Contracts

### Module Data Schema (served via `/api/modules` from Supabase)

```json
{
  "code": "string (e.g., 'A001')",
  "name": "string (e.g., '3D Printing Hacks')",
  "description": "string (module description text)",
  "school": "string (e.g., 'School of Applied Science')",
  "url": "string (URL to RP module page)"
}
```

### Diploma Mapping Schema (Supabase `rp_courses` → `/api/courses`)

```json
{
  "course_code": "R12",
  "course_name": "Diploma in Biomedical Science",
  "school_name": "School of Applied Science",
  "school_abbr": "SAS",
  "url": "https://www.rp.edu.sg/...",
  "general_modules": ["MGT1001", ...],
  "major_modules": ["BMS2001", ...],
  "discipline_modules": ["BMS3001", ...],
  "elective_modules": ["C270", ...],
  "industry_modules": ["BMS4001", ...]
}
```

Generated by `app/static/local-data/scripts/step3_scrape_diplomas.py` and imported into Supabase. Module comparison summaries are generated on-demand via Gemini (`/api/comparison/generate`).

### Review Schema (Supabase)

```sql
-- Stored in the shared Supabase PostgreSQL database.
-- The Flask backend proxies all reads/writes through API endpoints.
CREATE TABLE reviews (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    module_code text NOT NULL,
    rating integer NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment text NOT NULL DEFAULT '',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz,
    owner_token text
);

-- Index for fast per-module lookups.
CREATE INDEX idx_reviews_module_code ON reviews (module_code);

-- Foreign key to rp_modules (applied via migration).
ALTER TABLE reviews
    ADD CONSTRAINT fk_reviews_module
    FOREIGN KEY (module_code) REFERENCES rp_modules(module_code);
```

**Ownership model:** Reviews use anonymous token-based ownership. The
client generates a random UUID hex token (stored in `localStorage`) and
sends it as an `X-Owner-Token` header on create/update/delete. The
server stores this token in the `owner_token` column and validates it
before allowing mutations.

### Review Votes Schema

```sql
-- Supabase (PostgreSQL)
CREATE TABLE review_votes (
    id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    owner_token TEXT NOT NULL,
    vote_type SMALLINT NOT NULL CHECK (vote_type IN (1, -1)),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(review_id, owner_token)
);

-- SQLite (tests)
CREATE TABLE REVIEW_VOTES (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    REVIEW_ID INTEGER NOT NULL,
    OWNER_TOKEN TEXT NOT NULL,
    VOTE_TYPE INTEGER NOT NULL CHECK (VOTE_TYPE IN (1, -1)),
    CREATED_AT DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (REVIEW_ID) REFERENCES REVIEWS(ID) ON DELETE CASCADE,
    UNIQUE(REVIEW_ID, OWNER_TOKEN)
);
```

**Voting model:** One vote per user per review. The `owner_token` (same
token used for review ownership) identifies the voter. Changing a vote
replaces the previous one (upsert on `UNIQUE(review_id, owner_token)`).
Vote persistence is handled by `VoteRepository` in `app.py` (line 648),
which supports SQLite (tests), PostgreSQL, and Supabase backends.

### Backend API Endpoints

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|--------------|----------|
| `/api/modules` | GET | List all modules from Supabase | - | Array of module objects |
| `/api/courses` | GET | List all courses (diplomas) from Supabase | - | Array of course objects |
| `/api/minors` | GET | List all minor programmes from Supabase | - | Array of minor objects |
| `/api/career-paths` | GET | List all career paths | - | Array of career path objects |
| `/api/reviews` | GET | List all reviews (dashboard) | - | Array of review objects |
| `/api/reviews` | POST | Create a new review | `{ module_code, rating, comment }` | Review object |
| `/api/reviews/<module_code>` | GET | Get reviews for a module | - | Array of review objects |
| `/api/reviews/<review_id>` | PUT | Update a review | `{ rating, comment }` | Review object |
| `/api/reviews/<review_id>` | DELETE | Delete a review | - | 204 No Content |
| `/api/ratings` | GET | Get rating summary per module | - | `{ module_code: { average_rating, review_count, distribution } }` |
| `/api/reviews/<review_id>/vote` | GET | Get vote score and user's vote | - | `{ score, user_vote }` |
| `/api/reviews/<review_id>/vote` | POST | Add or update vote | `{ vote_type: 1 \| -1 }` | `{ score, user_vote }` |
| `/api/reviews/<review_id>/vote` | DELETE | Remove vote | - | `{ score, user_vote: 0 }` |
| `/api/reviews/votes` | POST | Bulk vote scores for multiple reviews | `{ review_ids: [...] }` | `{ votes: { review_id: { score, user_vote } } }` |
| `/api/comparison/generate` | POST | Generate Gemini comparison summary | `{ module1, module2 }` | Comparison text |
| `/api/gobot` | POST | Chatbot endpoint | `{ message }` | `{ response }` |

Each `distribution` contains string keys `"5"` through `"1"`, including ratings with a zero count. Example:

```json
{
  "C270": {
    "average_rating": 4.2,
    "review_count": 25,
    "distribution": { "5": 14, "4": 6, "3": 3, "2": 1, "1": 1 }
  }
}
```

### Page Structure

```
app/templates/base.html (Layout Partial - Tailwind CSS with glassmorphism)
├── Common HTML head, Tailwind CDN, Inter + Outfit fonts, Lucide Icons
├── Glass navbar (sticky, translucent, backdrop-blur)
├── {% block content %}{% endblock %} ← page-specific content injected here
├── Glass footer (dark slate background)
└── Mobile menu toggle script

app/templates/modules/index.html (Home/Search Page)
├── {% extends "base.html" %}
├── Hero Section (emerald→teal→cyan gradient, search bar)
├── Search Input + Filters Toggle Button
├── Collapsible Filter Panel (animated grid-rows transition)
│   ├── School Dropdown
│   ├── Diploma Dropdown (populated from /api/courses)
│   ├── Rating Dropdown (5 Stars, 4 Stars & Up, etc.)
│   ├── Active Toggle (modules in at least one diploma)
│   └── Clear All button
├── Search Results Section
│   ├── Results Count badge
│   └── Module Cards Grid (solid bg, hover lift shadow-xl)
│       ├── Module Code (uppercase tracking)
│       ├── Module Name (bold, hover color change)
│       ├── Description (truncated, slate-500)
│       ├── School Badge (rounded-full)
│       ├── Rating (amber stars)
│       └── Action Buttons (Source link)
├── Pagination (9 per page, ellipsis, keyboard nav)
├── Module Detail Modal (custom implementation)
│   ├── Modal overlay (backdrop-blur)
│   ├── Modal panel (rounded-2xl, solid bg)
│   ├── Full Module Details
│   ├── Diploma List
│   ├── Reviews Section (Rating + Comments)
│   │   └── Vote Button Group (thumbs-up, score, thumbs-down)
│   └── Review Submission Form

app/templates/modules/comparison.html (Comparison Page)
├── {% extends "base.html" %}
├── Comparison Hero (subtle gradient background)
├── Comparison Panel (solid card)
│   ├── Module Search Inputs
│   ├── Selected Module Chips
│   ├── VS Badge (emerald gradient, shadow-glow)
│   └── Comparison Table (striped rows, primary-tinted headers)

app/templates/modules/reviews.html (Review Dashboard)
├── {% extends "base.html" %}
├── Dashboard Hero (gradient background)
├── Stat Cards (solid bg)
├── Review Toolbar (filters)
├── Review Cards Grid (solid bg)
│   └── Vote Button Group (thumbs-up, score, thumbs-down)
└── Edit Review Modal (custom implementation)

app/static/js/gobot.js (Chatbot - Gemini-powered)
├── GoBot object with welcome popup
├── Chat UI with quick-send buttons
├── Message history in localStorage
└── POST /api/gobot communication

app/static/js/bookmark.js (Favorites - localStorage)
├── BookmarkManager with toggle/add/remove
└── localStorage persistence

app/static/js/share.js (Share functionality)
├── getShareUrl(), copyLink(), exportCSV()
└── Toast notifications
```

## 5. Acceptance Criteria

### Search Functionality
- **AC-001**: Given user is on the home page, When user types in search input, Then matching modules appear in real-time
- **AC-002**: Given user types "A001", When search filters, Then only modules with code containing "A001" are shown
- **AC-003**: Given user types "biology", When search filters, Then modules with "biology" in name or description are shown
- **AC-004**: Given no results match, When search is performed, Then "No modules found" message is displayed
- **AC-005**: Given user selects a school from filter panel, When search filters, Then only modules from that school are shown
- **AC-006**: Given user selects a diploma from filter panel, When search filters, Then only modules included in that diploma are shown
- **AC-007**: Given user selects a rating filter, When search filters, Then only modules with average rating at or above the selected value are shown
- **AC-008**: Given user toggles "Active" filter, When search filters, Then only modules appearing in at least one diploma are shown
- **AC-009**: Given filters are applied, When URL is refreshed, Then filter state is restored from URL params

### Module Display
- **AC-010**: Given search results are displayed, When user views the list, Then each module shows code, name, description, category, and school
- **AC-011**: Given module has a URL, When user views module card, Then external link button is visible and clickable

### Module Detail
- **AC-012**: Given user clicks a module, When detail view opens, Then full description and diploma list are displayed
- **AC-013**: Given module has diplomas, When detail view opens, Then diploma names are listed with links to diploma pages

### Review System
- **AC-014**: Given user is on module detail, When user submits review with rating and comment, Then review is saved to backend database
- **AC-015**: Given reviews exist for a module, When user views module detail, Then existing reviews are displayed with rating and timestamp
- **AC-016**: Given user submits review, When page reloads, Then review persists in database

### Module Comparison
- **AC-017**: Given user is on comparison page, When user searches and selects two modules, Then comparison table displays side-by-side
- **AC-018**: Given two modules are selected, When comparison table loads, Then module attributes are compared in rows

### Responsive Design
- **AC-019**: Given user is on mobile (< 768px), When viewing search results, Then modules display in single column
- **AC-020**: Given user is on tablet (768px-1024px), When viewing search results, Then modules display in 2 columns
- **AC-021**: Given user is on desktop (> 1024px), When viewing search results, Then modules display in 3 columns

### Loading States
- **AC-022**: Given page is loading, When data is being fetched, Then loading animation is displayed
- **AC-023**: Given search is filtering, When results are updating, Then subtle loading indicator is shown

### Rating Distribution
- **AC-024**: Given a module has reviews, When its detail window opens, Then all five rating buckets are shown with counts and bars proportional to the total review count
- **AC-025**: Given a module has no reviews, When its detail window opens, Then "No ratings yet" is shown and the distribution is hidden

### Review Voting
- **AC-026**: Given user views a review, When user clicks upvote, Then score increments by 1, upvote button fills, and downvote clears
- **AC-027**: Given user views a review, When user clicks downvote, Then score decrements by 1, downvote button fills, and upvote clears
- **AC-028**: Given user has voted on a review, When user clicks the same vote again, Then vote is removed and score returns to previous value
- **AC-029**: Given user is the review owner, When user views vote buttons, Then vote buttons are disabled or hidden
- **AC-030**: Given user has voted, When page reloads, Then vote state persists (filled icon for active vote)

## 6. Test Automation Strategy

- **Test Levels**: Automated API tests (pytest), manual browser testing
- **Frameworks**: pytest for backend API tests
- **Test Data Management**: SQLite in-memory database for isolated tests
- **Coverage Requirements**: All API endpoints tested, manual testing for UI
- **Performance Testing**: Test with full Supabase dataset, ensure smooth filtering
- **API Testing**: Automated pytest suite for Flask endpoints
- **Database Testing**: Verify Supabase operations via mocked client in tests

## 7. Rationale & Context

**Design Decisions:**
1. **Tailwind CSS (v3 CDN)**: Utility-first approach enables rapid prototyping, consistent design tokens via CSS custom properties, and zero build step with CDN usage
2. **Glassmorphism design system**: Modern, visually impressive aesthetic with translucent backgrounds, backdrop-blur, and subtle borders for depth (navbar only; cards go solid)
3. **Custom modal implementation**: Replaced Bootstrap Modal with vanilla JS modal to eliminate Bootstrap JS dependency while maintaining full control over modal behavior
4. **Inter + Outfit font family**: Inter for body text, Outfit for display headings — clean, modern sans-serif optimized for screen readability
5. **Emerald color palette**: RP brand green as single accent color, restrained to CTAs + active states
6. **Client-side filtering**: No server needed for search, instant feedback, works offline
7. **Supabase for modules and reviews**: Managed PostgreSQL with real-time capabilities, no self-hosted database
8. **Flask app structure**: Standard Python Flask layout with templates, static, and data separation
9. **Collapsible filter panel**: School, diploma, rating, and active filters in a toggleable panel, state persisted in URL params
10. **GoBot chatbot**: Gemini-powered chatbot with early-return handler pipeline, no hardcoded word lists, data-driven heuristics
11. **Anonymous ownership**: Token-based ownership for reviews without user authentication, using UUID hex stored in localStorage
12. **Triple-branch repository pattern**: `ReviewRepository` and `VoteRepository` support SQLite (tests), PostgreSQL, and Supabase backends

**Trade-offs:**
- Client-side filtering requires loading entire dataset upfront
- No user authentication means reviews are anonymous and not verifiable
- Supabase dependency means reviews require network connectivity
- Tailwind CDN adds runtime CSS generation (acceptable for student project scale)

## 8. Dependencies & External Integrations

### Data Dependencies
- **DAT-001**: Supabase `rp_modules` table - Module dataset stored in PostgreSQL
- **DAT-002**: Supabase `rp_courses` table - Diploma/course data scraped from RP website
- **DAT-003**: Supabase `rp_minors` table - Minor programme data scraped from RP website
- **DAT-004**: Gemini API — On-demand module comparison generation and GoBot chatbot responses
- **DAT-005**: Career path data (Supabase or local JSON) — Module-to-career matching for GoBot

### External Links
- **EXT-001**: RP Module Pages - Links to official module information
- **EXT-002**: RP Diploma Pages - Links to diploma program pages

### Infrastructure Dependencies
- **INF-001**: Modern web browser with JavaScript support
- **INF-002**: Tailwind CSS via CDN (runtime CSS generation)
- **INF-003**: Inter + Outfit fonts via Google Fonts CDN
- **INF-004**: Lucide Icons via CDN (`unpkg.com/lucide`)
- **INF-005**: Python 3.12+ runtime
- **INF-006**: Flask web framework
- **INF-007**: Supabase project with `rp_modules`, `rp_courses`, `rp_minors`, `reviews`, `review_votes`, and `career_paths` tables
- **INF-008**: Scraping pipeline (`app/static/local-data/scripts/`) for automated data collection (5 steps: tokens, modules, diplomas, minors, career paths)
- **INF-009**: Gemini API key for comparison generation and GoBot chatbot

### Backend Dependencies
- **DEP-001**: Flask 3.1.3 - Web framework
- **DEP-002**: supabase 2.31.0 - Supabase Python client
- **DEP-003**: python-dotenv 1.2.2 - Environment variable loading
- **DEP-004**: SQLite3 - Local review database (tests and offline fallback)
- **DEP-005**: pytest>=8.0,<10.0 - Test framework
- **DEP-006**: Flask-WTF>=1.2.0 - CSRF protection (API routes exempt)
- **DEP-007**: Flask-Limiter>=3.0.0 - Rate limiting (20/hr POST, 10/hr PUT/DELETE)
- **DEP-008**: psycopg2-binary>=2.9,<3.0 - PostgreSQL adapter for production database
- **DEP-009**: playwright>=1.50,<2.0 - Browser automation for scraping (token extraction)
- **DEP-010**: requests>=2.32,<3.0 - HTTP client for scraping scripts
- **DEP-011**: httpx>=0.27,<0.29 - Async HTTP client
- **DEP-012**: crawl4ai>=0.2.0 - Web crawling framework
- **DEP-013**: beautifulsoup4>=4.12 - HTML parsing for scraping

## 9. Examples & Edge Cases

### Search Edge Cases
- Empty search query: Show all modules or prompt user
- Special characters in search: Handle gracefully, escape if needed
- Very long module descriptions: Truncate with "Read more" option
- Module with no category: Display without category badge

### Rating Edge Cases
- User rates same module multiple times: Update existing rating
- No ratings yet: Show empty stars or "No ratings"
- All ratings are same value: Display that value as average

### Comment Edge Cases
- Empty comment submission: Prevent submission or show validation
- Very long comments: Limit character count or allow scrolling
- No comments yet: Show "No comments yet" message

### Voting Edge Cases
- User votes on own review: Prevent or disable vote buttons
- User changes vote: Upsert replaces previous vote, score updates
- User removes vote: Delete vote row, score updates
- Review deleted with votes: CASCADE delete removes all associated votes
- Multiple rapid clicks: Debounce or let upsert handle idempotency

## 10. Validation Criteria

- [x] All user stories implemented and functional
- [x] Search filters correctly across all module fields
- [x] School filter dropdown works correctly
- [x] Diploma filter dropdown works correctly (populated from /api/courses)
- [x] Rating filter works correctly (minimum average rating)
- [x] Active filter works correctly (modules in at least one diploma)
- [x] Filter state persisted in URL params
- [x] Module detail shows complete information and diploma list
- [x] Review system saves to Supabase via Flask API
- [x] Reviews display correctly with rating and timestamp
- [x] Module comparison page works correctly
- [x] Responsive design works on mobile, tablet, and desktop
- [x] Loading animations display during data operations
- [x] External links open in new tabs
- [x] No JavaScript errors in browser console
- [x] Tailwind CSS CDN loads correctly
- [x] Glassmorphism effects render properly (backdrop-blur, translucent backgrounds)
- [x] Custom modals open and close correctly (keyboard, click-outside, close button)
- [x] Flask backend starts and serves API endpoints
- [x] Module data loads from Supabase via /api/modules
- [ ] Cross-browser testing (Chrome, Firefox, Safari, Edge)

## 11. Related Specifications / Further Reading

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Tailwind CSS Theme Variables](https://tailwindcss.com/docs/theme)
- [RP Diploma List](https://www.rp.edu.sg/education/diplomas/)
- [RP Module List](https://www.rp.edu.sg/education/modules/)
- [RP Updated Modules](https://lcs.rp.edu.sg/RPModuleSynopsis/)
- [SaaS Landing Page Reference](https://saaslandingpage.com/)
- [oklch Color Picker](https://oklch.com/)

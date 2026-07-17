---
title: ModuleGo - Republic Polytechnic Module Viewer Design Specification
version: 4.0
date_created: 2026-06-29
last_updated: 2026-07-17
owner: Developer
status: 'In progress'
tags: ['design', 'frontend', 'backend', 'vanilla-js', 'bootstrap', 'flask', 'supabase']
---

# Introduction

ModuleGo is a responsive web application that allows Republic Polytechnic students to search for modules, view module details, discover which diplomas offer each module, compare modules side-by-side, and leave reviews. The application addresses the limitation of the official RP Module viewer by providing a more intuitive and comprehensive module exploration experience.

## 1. Purpose & Scope

**Purpose:** Define the design system, UI components, and interaction patterns for the ModuleGo application.

**Scope:** Full-stack web application with:
- Frontend: Vanilla JS, CSS/Bootstrap, and HTML
- Backend: Python Flask server with Supabase PostgreSQL (modules and reviews)
- API endpoints for module data and review management

**Audience:** Republic Polytechnic students seeking to explore modules and their associated diplomas.

**Assumptions:**
- Module data is stored in Supabase `rp_modules` table and served via `/api/modules`
- Diploma-to-module mapping is hardcoded in `app/static/data/diploma.json`
- Review data (ratings and comments) is stored in Supabase `reviews` table
- Backend server runs on Python Flask and proxies all Supabase calls
- SQLite is used only for automated tests

## 2. Definitions

| Term | Definition |
|------|------------|
| Module | A course unit offered at Republic Polytechnic, identified by a module code (e.g., A001) |
| Diploma | A full-time program of study at RP (e.g., Diploma in Applied AI & Analytics) |
| School | Academic division at RP (e.g., School of Infocomm) |
| Client-side filtering | Searching/filtering data in the browser without server requests |

## 3. Requirements, Constraints & Guidelines

### Core Requirements

- **REQ-001**: User can enter a search query into an input field
- **REQ-002**: User can submit the query (via typing, pressing Enter, or clicking search button)
- **REQ-003**: Search filters modules by Module Code, Module Name, Description, Category, or School
- **REQ-004**: Search results display as a list showing Module Code, Module Name, Description, Category, and School
- **REQ-005**: Clicking a module displays a list of diplomas offering that module
- **REQ-006**: Each module entry includes a link to the external RP module page (url field)
- **REQ-007**: User can filter modules by School using dropdown filter
- **REQ-008**: User can compare two modules side-by-side
- **REQ-009**: User can leave reviews with ratings (1-5) and comments on modules
- **REQ-010**: Reviews are stored in Supabase `reviews` table
- **REQ-011**: User can view existing reviews for each module

### Bonus Requirements

- **REQ-B01**: Responsive design works on desktop, tablet, and mobile viewports
- **REQ-B02**: Loading animation displayed during initial data load
- **REQ-B03**: Module comparison page with side-by-side table view
- **REQ-B04**: School filter dropdown for narrowing search results

### Constraints

- **CON-001**: Use only Vanilla JavaScript (no frameworks like React, Vue, Angular)
- **CON-002**: Use Bootstrap 5 for styling and responsive grid
- **CON-003**: Use HTML5 semantic elements
- **CON-004**: Backend uses Python Flask with Supabase PostgreSQL
- **CON-005**: Module data is stored in Supabase, diploma data is static JSON
- **CON-006**: Project follows Flask app structure: `app/templates/` for HTML, `app/static/` for assets
- **CON-007**: Frontend never calls Supabase directly; all requests go through Flask API

### Design Guidelines

- **GUD-001**: Follow RP brand colors: Green (#00A651), Black (#1a1a1a), White (#ffffff)
- **GUD-002**: Use Bootstrap 5 grid system (12-column)
- **GUD-003**: Maintain WCAG AA contrast ratios for accessibility
- **GUD-004**: Mobile-first responsive approach
- **GUD-005**: Clean, functional UI prioritizing information hierarchy

## 4. Interfaces & Data Contracts

### Module Data Schema (served via `/api/modules` from Supabase)

```json
{
  "code": "string (e.g., 'A001')",
  "name": "string (e.g., '3D Printing Hacks')",
  "description": "string (module description text)",
  "school": "string (e.g., 'School of Applied Science')",
  "url": "string (URL to RP module page)",
  "features": "string (auto-generated comparison features)",
  "suitableFor": "string (auto-generated suitability description)"
}
```

The `/api/modules` endpoint maps Supabase columns (`module_code`,
`module_name`, `module_description`, `school`, `link`) to the frontend
format and generates `features` and `suitableFor` fields server-side.

### Diploma Mapping Schema (app/static/data/diploma.json)

```json
{
  "A001": ["Diploma in Mechatronics", "Diploma in Engineering"],
  "A103": ["Diploma in Biomedical Science", "Diploma in Sports Science"]
}
```

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
    updated_at timestamptz
);

-- Index for fast per-module lookups.
CREATE INDEX idx_reviews_module_code ON reviews (module_code);

-- Foreign key to rp_modules (applied via migration).
ALTER TABLE reviews
    ADD CONSTRAINT fk_reviews_module
    FOREIGN KEY (module_code) REFERENCES rp_modules(module_code);
```

### Backend API Endpoints

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|--------------|----------|
| `/api/modules` | GET | List all modules from Supabase | - | Array of module objects |
| `/api/reviews` | GET | List all reviews (dashboard) | - | Array of review objects |
| `/api/reviews` | POST | Create a new review | `{ module_code, rating, comment }` | Review object |
| `/api/reviews/<module_code>` | GET | Get reviews for a module | - | Array of review objects |
| `/api/reviews/<review_id>` | PUT | Update a review | `{ rating, comment }` | Review object |
| `/api/reviews/<review_id>` | DELETE | Delete a review | - | 204 No Content |
| `/api/ratings` | GET | Get average rating per module | - | `{ module_code: { average_rating, review_count } }` |

### Page Structure

> [!TIP]
> **Express equivalent:** `base.html` works like a partial (e.g., `partials/layout.html`) that all pages extend. The `{% raw %}{% block content %}{% endraw %}` placeholder is where page-specific content goes, similar to how you'd `<%- include() %>` shared components in Express.

```
app/templates/base.html (Layout Partial - like partials/layout.ejs)
├── Common HTML head, Bootstrap CDN, meta tags
├── Header/Nav (shared across all pages)
├── {% raw %}{% block content %}{% endblock %}{% endraw %} ← page-specific content injected here
└── Footer (shared across all pages)

app/templates/modules/index.html (Home/Search Page - like views/modules/index.html)
├── {% raw %}{% extends "base.html" %}{% endraw %}
├── Hero Section (Search Input + School Filter)
├── Search Results Section
│   ├── Results Count
│   └── Module Cards List
│       ├── Module Code
│       ├── Module Name
│       ├── Description (truncated)
│       ├── Category Badge
│       ├── School
│       └── External Link Button
├── Module Detail Modal
│   ├── Full Module Details
│   ├── Diploma List
│   ├── Reviews Section (Rating + Comments)
│   └── Review Submission Form

app/templates/modules/comparison.html (Comparison Page - like views/modules/comparison.html)
├── {% raw %}{% extends "base.html" %}{% endraw %}
├── Comparison Hero Section
├── Module Search Inputs (2)
└── Comparison Table
```

## 5. Acceptance Criteria

### Search Functionality
- **AC-001**: Given user is on the home page, When user types in search input, Then matching modules appear in real-time
- **AC-002**: Given user types "A001", When search filters, Then only modules with code containing "A001" are shown
- **AC-003**: Given user types "biology", When search filters, Then modules with "biology" in name or description are shown
- **AC-004**: Given no results match, When search is performed, Then "No modules found" message is displayed
- **AC-005**: Given user selects a school from dropdown, When search filters, Then only modules from that school are shown

### Module Display
- **AC-006**: Given search results are displayed, When user views the list, Then each module shows code, name, description, category, and school
- **AC-007**: Given module has a URL, When user views module card, Then external link button is visible and clickable

### Module Detail
- **AC-008**: Given user clicks a module, When detail view opens, Then full description and diploma list are displayed
- **AC-009**: Given module has diplomas, When detail view opens, Then diploma names are listed with links to diploma pages

### Review System
- **AC-010**: Given user is on module detail, When user submits review with rating and comment, Then review is saved to backend database
- **AC-011**: Given reviews exist for a module, When user views module detail, Then existing reviews are displayed with rating and timestamp
- **AC-012**: Given user submits review, When page reloads, Then review persists in database

### Module Comparison
- **AC-013**: Given user is on comparison page, When user searches and selects two modules, Then comparison table displays side-by-side
- **AC-014**: Given two modules are selected, When comparison table loads, Then module attributes are compared in rows

### Responsive Design
- **AC-015**: Given user is on mobile (< 768px), When viewing search results, Then modules display in single column
- **AC-016**: Given user is on tablet (768px-1024px), When viewing search results, Then modules display in 2 columns
- **AC-017**: Given user is on desktop (> 1024px), When viewing search results, Then modules display in 3 columns

### Loading States
- **AC-018**: Given page is loading, When data is being fetched, Then loading animation is displayed
- **AC-019**: Given search is filtering, When results are updating, Then subtle loading indicator is shown

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
1. **Bootstrap 5**: Rapid development, built-in responsive grid, consistent components
2. **Client-side filtering**: No server needed for search, instant feedback, works offline
3. **Supabase for modules and reviews**: Managed PostgreSQL with real-time capabilities, no self-hosted database
4. **Flask app structure**: Standard Python Flask layout with templates, static, and data separation
5. **Green theme**: Matches RP brand identity for institutional familiarity

**Trade-offs:**
- Client-side filtering requires loading entire dataset upfront
- No user authentication means reviews are anonymous and not verifiable
- Supabase dependency means reviews require network connectivity

## 8. Dependencies & External Integrations

### Data Dependencies
- **DAT-001**: Supabase `rp_modules` table - Module dataset stored in PostgreSQL
- **DAT-002**: `app/static/data/diploma.json` - Hardcoded diploma mapping

### External Links
- **EXT-001**: RP Module Pages - Links to official module information
- **EXT-002**: RP Diploma Pages - Links to diploma program pages

### Infrastructure Dependencies
- **INF-001**: Modern web browser with JavaScript support
- **INF-002**: Bootstrap 5 CSS/JS via CDN
- **INF-003**: Python 3.x runtime
- **INF-004**: Flask web framework
- **INF-005**: Supabase project with `rp_modules` and `reviews` tables

### Backend Dependencies
- **DEP-001**: Flask 3.0.3 - Web framework
- **DEP-002**: supabase 2.31.0 - Supabase Python client
- **DEP-003**: python-dotenv 1.1.0 - Environment variable loading
- **DEP-004**: SQLite3 - Database (automated tests only)
- **DEP-005**: pytest>=8.0,<10.0 - Test framework

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

## 10. Validation Criteria

- [x] All user stories implemented and functional
- [x] Search filters correctly across all module fields
- [x] School filter dropdown works correctly
- [x] Module detail shows complete information and diploma list
- [x] Review system saves to Supabase via Flask API
- [x] Reviews display correctly with rating and timestamp
- [x] Module comparison page works correctly
- [x] Responsive design works on mobile, tablet, and desktop
- [x] Loading animations display during data operations
- [x] External links open in new tabs
- [x] No JavaScript errors in browser console
- [x] Bootstrap CDN loads correctly
- [x] Flask backend starts and serves API endpoints
- [x] Module data loads from Supabase via /api/modules
- [ ] Cross-browser testing (Chrome, Firefox, Safari, Edge)

## 11. Related Specifications / Further Reading

- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.3/)
- [RP Diploma List](https://www.rp.edu.sg/education/diplomas/)
- [RP Module List](https://www.rp.edu.sg/education/modules/)
- [RP Updated Modules](https://lcs.rp.edu.sg/RPModuleSynopsis/)

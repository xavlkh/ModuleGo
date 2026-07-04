---
goal: ModuleGo - Republic Polytechnic Module Viewer Implementation
version: 3.0
date_created: 2026-06-29
last_updated: 2026-07-05
owner: Developer
status: 'In progress'
tags: ['feature', 'frontend', 'backend', 'vanilla-js', 'bootstrap', 'flask', 'sqlite', 'restructure']
---

# Introduction

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

Implementation plan for ModuleGo, a responsive module search application for Republic Polytechnic students. The application uses Vanilla JS, Bootstrap 5, and HTML for the frontend, with Python Flask and SQLite for the backend review system. The project follows a standard Flask app structure with `app/templates/` for HTML, `app/static/` for CSS/JS, and `app/data/` for JSON data files.

## 1. Requirements & Constraints

- **REQ-001**: User can enter a search query into an input field
- **REQ-002**: User can submit the query (via typing, pressing Enter, or clicking search button)
- **REQ-003**: Search filters modules by Module Code, Module Name, Description, Category, or School
- **REQ-004**: Search results display as a list with Module Code, Name, Description, Category, School
- **REQ-005**: Clicking a module displays a list of diplomas offering that module
- **REQ-006**: Each module entry includes a link to the external RP module page
- **REQ-007**: User can filter modules by School using dropdown filter
- **REQ-008**: User can compare two modules side-by-side
- **REQ-009**: User can leave reviews with ratings (1-5) and comments on modules
- **REQ-010**: Reviews are stored in backend database (SQLite)
- **REQ-011**: User can view existing reviews for each module
- **REQ-B01**: Responsive design works on desktop, tablet, and mobile
- **REQ-B02**: Loading animation displayed during initial data load
- **REQ-B03**: Module comparison page with side-by-side table view
- **REQ-B04**: School filter dropdown for narrowing search results
- **CON-001**: Use only Vanilla JavaScript (no frameworks)
- **CON-002**: Use Bootstrap 5 for styling and responsive grid
- **CON-003**: Use HTML5 semantic elements
- **CON-004**: Backend uses Python Flask with SQLite database
- **CON-005**: Module data is static JSON file
- **GUD-001**: Follow RP brand colors: Green (#00A651), Black (#1a1a1a), White (#ffffff)

## 2. Implementation Steps

### Implementation Phase 1: Project Setup & Data Preparation

- GOAL-001: Set up project structure and prepare data files

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create project directory structure: `index.html`, `css/`, `js/`, `data/` | ✅ | 2026-06-29 |
| TASK-002 | Copy `rp-modules-final.json` to `data/` folder | ✅ | 2026-06-29 |
| TASK-003 | Create `data/diplomas.json` with hardcoded module-to-diploma mapping | ✅ | 2026-06-29 |
| TASK-004 | Create `index.html` with Bootstrap 5 CDN links and basic HTML structure | ✅ | 2026-06-29 |
| TASK-005 | Create `css/styles.css` with RP brand color variables and base styles | ✅ | 2026-06-29 |

### Implementation Phase 2: Core UI Components

- GOAL-002: Build the main page layout and search interface

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-006 | Create header with RP logo and navigation | ✅ | 2026-06-29 |
| TASK-007 | Create hero section with search input and search button | ✅ | 2026-06-29 |
| TASK-008 | Create search results container with results count display | ✅ | 2026-06-29 |
| TASK-009 | Create module card template with code, name, description, category, school, and external link | ✅ | 2026-06-29 |
| TASK-010 | Create footer with RP branding | ✅ | 2026-06-29 |
| TASK-011 | Create loading animation component (spinner or skeleton) | ✅ | 2026-06-29 |

### Implementation Phase 3: Search Functionality

- GOAL-003: Implement client-side module search and filtering

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-012 | Create `js/data.js` - Load and parse module data from JSON | ✅ | 2026-06-29 |
| TASK-013 | Create `js/search.js` - Implement search filter function (code, name, description, category, school) | ✅ | 2026-06-29 |
| TASK-014 | Create `js/ui.js` - Implement render function to display filtered modules as cards | ✅ | 2026-06-29 |
| TASK-015 | Add event listeners for search input (real-time filtering on keyup) | ✅ | 2026-06-29 |
| TASK-016 | Add event listener for search button click and Enter key | ✅ | 2026-06-29 |
| TASK-017 | Implement "No results found" message when search yields no matches | ✅ | 2026-06-29 |

### Implementation Phase 4: Module Detail View

- GOAL-004: Create module detail modal/section with diploma list

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-018 | Create `js/detail.js` - Module detail modal/section component | ✅ | 2026-06-29 |
| TASK-019 | Create detail view with full module description, code, name, category, school | ✅ | 2026-06-29 |
| TASK-020 | Create diploma list section in detail view | ✅ | 2026-06-29 |
| TASK-021 | Load diploma mapping data and match to current module | ✅ | 2026-06-29 |
| TASK-022 | Display diploma names with links to RP diploma pages | ✅ | 2026-06-29 |
| TASK-023 | Add click handler on module cards to open detail view | ✅ | 2026-06-29 |
| TASK-024 | Add close button/handler for detail view | ✅ | 2026-06-29 |

### Implementation Phase 5: Backend Review System

- GOAL-005: Implement Flask backend with SQLite for review persistence

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-025 | Create `app.py` - Flask backend with SQLite database | ✅ | 2026-07-04 |
| TASK-026 | Implement `/api/reviews` POST endpoint for creating reviews | ✅ | 2026-07-04 |
| TASK-027 | Implement `/api/reviews/<module_code>` GET endpoint for reading reviews | ✅ | 2026-07-04 |
| TASK-028 | Create `requirements.txt` with Flask dependencies | ✅ | 2026-07-04 |
| TASK-029 | Update `js/detail.js` to use fetch API for review operations | ✅ | 2026-07-04 |
| TASK-030 | Create review submission form with rating dropdown and comment textarea | ✅ | 2026-07-04 |
| TASK-031 | Implement review display with rating stars and timestamp | ✅ | 2026-07-04 |

### Implementation Phase 6: Module Comparison

- GOAL-006: Implement module comparison feature

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-032 | Create `comparison.html` page with comparison UI | ✅ | 2026-07-04 |
| TASK-033 | Create `js/comparison.js` - Module comparison logic | ✅ | 2026-07-04 |
| TASK-034 | Implement dual search inputs for module selection | ✅ | 2026-07-04 |
| TASK-035 | Create comparison table with side-by-side view | ✅ | 2026-07-04 |

### Implementation Phase 7: School Filter & Polish

- GOAL-007: Add school filtering and polish UI

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-036 | Add school filter dropdown to search interface | ✅ | 2026-07-04 |
| TASK-037 | Update search logic to include school filtering | ✅ | 2026-07-04 |
| TASK-038 | Add hover effects on module cards | ✅ | 2026-06-29 |
| TASK-039 | Add transition animations for detail view open/close | ✅ | 2026-06-29 |
| TASK-040 | Test and fix responsive design on mobile, tablet, desktop | ✅ | 2026-06-29 |
| TASK-041 | Cross-browser testing (Chrome, Firefox, Safari, Edge) | ✅ | 2026-07-05 |

### Implementation Phase 8: Project Restructuring to Flask App Layout

- GOAL-008: Reorganize project into standard Flask application structure

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-042 | Create `app/` directory with `templates/`, `static/`, and `data/` subdirectories | ✅ | 2026-07-05 |
| TASK-043 | Move `index.html` and `comparison.html` to `app/templates/modules/` | ✅ | 2026-07-05 |
| TASK-044 | Create `app/templates/base.html` base layout template | ✅ | 2026-07-05 |
| TASK-045 | Move `css/styles.css` to `app/static/css/` | ✅ | 2026-07-05 |
| TASK-046 | Move all `js/*.js` files to `app/static/js/` | ✅ | 2026-07-05 |
| TASK-047 | Move `data/` files to `app/data/` | ✅ | 2026-07-05 |
| TASK-048 | Move `spec/` and `plan/` docs to `docs/` directory | ✅ | 2026-07-05 |
| TASK-049 | Create `tests/` directory for future test files | ✅ | 2026-07-05 |
| TASK-050 | Create `.env.example` for environment configuration | ✅ | 2026-07-05 |
| TASK-051 | Update `.gitignore` for new project structure | ✅ | 2026-07-05 |

## 3. Alternatives

- **ALT-001**: React/Vue framework - Rejected due to constraint CON-001 (Vanilla JS only)
- **ALT-002**: LocalStorage for review persistence - Rejected in favor of SQLite database for better data integrity
- **ALT-003**: IndexedDB for persistence - Rejected as SQLite provides better querying capabilities
- **ALT-004**: CSS-only accordion - Rejected in favor of Bootstrap JS accordion for better accessibility
- **ALT-005**: Separate rating and comment systems - Rejected in favor of unified review system

## 4. Dependencies

- **DEP-001**: Bootstrap 5.3 CSS/JS via CDN
- **DEP-002**: Bootstrap Icons via CDN
- **DEP-003**: rp-modules-final.json dataset
- **DEP-004**: Flask 3.0.3 (Python web framework) -- *Express equivalent*
- **DEP-005**: SQLite3 (Python built-in database)
- **DEP-006**: Python 3.x runtime
- **DEP-007**: Flask app structure (templates, static, data directories) -- *Like Express with EJS views*

## 5. Files

| Flask Path | Express Equivalent | Description |
|------------|-------------------|-------------|
| `app/templates/modules/index.html` | `views/modules/index.html` | Main search and browse page |
| `app/templates/modules/comparison.html` | `views/modules/comparison.html` | Module comparison page |
| `app/templates/base.html` | `partials/layout.html` | Layout partial with shared nav/footer |
| `app/static/css/styles.css` | `public/css/styles.css` | Custom CSS styles and RP theme |
| `app/static/js/data.js` | `public/js/data.js` | Data loading and parsing |
| `app/static/js/search.js` | `public/js/search.js` | Search/filter functionality |
| `app/static/js/ui.js` | `public/js/ui.js` | UI rendering functions |
| `app/static/js/detail.js` | `public/js/detail.js` | Module detail view with review system |
| `app/static/js/comparison.js` | `public/js/comparison.js` | Module comparison logic |
| `app/static/js/app.js` | `public/js/app.js` | Main application initialization |
| `app/static/js/generate-comparison-fields.js` | `public/js/generate-comparison-fields.js` | Data processing utility |
| `app.py` | `server.js` | Flask backend with SQLite database |
| `requirements.txt` | `package.json` | Python dependencies |
| `app/static/data/rp-modules-final.json` | `data/rp-modules-final.json` | Module dataset |
| `app/static/data/diploma.json` | `data/diploma.json` | Diploma mapping data |

## 6. Testing

- **TEST-001**: Search returns correct results for module code query (e.g., "A001")
- **TEST-002**: Search returns correct results for module name query (e.g., "biology")
- **TEST-003**: Search returns correct results for description query
- **TEST-004**: School filter correctly filters modules by selected school
- **TEST-005**: Module detail shows complete information
- **TEST-006**: Diploma list displays correctly for modules with mapped diplomas
- **TEST-007**: Review submission saves to SQLite database via Flask API
- **TEST-008**: Reviews display correctly with rating and timestamp
- **TEST-009**: Module comparison page loads and displays two modules side-by-side
- **TEST-010**: Responsive design works at 375px (mobile), 768px (tablet), 1024px+ (desktop)
- **TEST-011**: Loading animation displays during data load
- **TEST-012**: External links open in new tab
- **TEST-013**: Flask backend starts and serves API endpoints correctly
- **TEST-014**: SQLite database initializes and stores reviews correctly

## 7. Risks & Assumptions

- **RISK-001**: Large dataset (4000+ modules) may cause slow initial load - Mitigation: Show loading indicator
- **RISK-002**: SQLite database may have concurrency issues with multiple users - Mitigation: Acceptable for single-user development
- **RISK-003**: Diploma mapping may be incomplete - Mitigation: Show "No diploma information available" for unmapped modules
- **RISK-004**: Flask backend must be running for review functionality - Mitigation: Show error message if server not available
- **ASSUMPTION-001**: Users have modern browsers with JavaScript support
- **ASSUMPTION-002**: Bootstrap CDN is accessible
- **ASSUMPTION-003**: Module data is accurate and up-to-date
- **ASSUMPTION-004**: Python 3.x is installed on the server

## 8. Related Specifications / Further Reading

- [ModuleGo Design Specification](./spec-modulego-design.md)
- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.3/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [RP Diploma List](https://www.rp.edu.sg/education/diplomas/)
- [RP Module List](https://www.rp.edu.sg/education/modules/)

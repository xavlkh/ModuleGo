---
goal: ModuleGo - Republic Polytechnic Module Viewer Implementation
version: 1.0
date_created: 2026-06-29
last_updated: 2026-06-29
owner: Developer
status: 'Planned'
tags: ['feature', 'frontend', 'vanilla-js', 'bootstrap']
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Implementation plan for ModuleGo, a responsive module search application for Republic Polytechnic students. The application uses Vanilla JS, Bootstrap 5, and HTML to provide module search, detail viewing, and anonymous rating/commenting features.

## 1. Requirements & Constraints

- **REQ-001**: User can enter a search query into an input field
- **REQ-002**: User can submit the query (via typing, pressing Enter, or clicking search button)
- **REQ-003**: Search filters modules by Module Code, Module Name, Description, Category, or School
- **REQ-004**: Search results display as a list with Module Code, Name, Description, Category, School
- **REQ-005**: Clicking a module displays a list of diplomas offering that module
- **REQ-006**: Each module entry includes a link to the external RP module page
- **REQ-B01**: Responsive design works on desktop, tablet, and mobile
- **REQ-B02**: Loading animation displayed during initial data load
- **REQ-B03**: Anonymous commenting system on module detail pages
- **REQ-B04**: Anonymous 1-5 star rating system on module detail pages
- **REQ-B05**: Average module rating displayed on search results page
- **REQ-B06**: Comments displayed in accordion/collapsible section
- **CON-001**: Use only Vanilla JavaScript (no frameworks)
- **CON-002**: Use Bootstrap 5 for styling and responsive grid
- **CON-003**: Use HTML5 semantic elements
- **CON-004**: No backend/server required
- **CON-005**: Data persistence via browser LocalStorage only
- **GUD-001**: Follow RP brand colors: Green (#00A651), Black (#1a1a1a), White (#ffffff)

## 2. Implementation Steps

### Implementation Phase 1: Project Setup & Data Preparation

- GOAL-001: Set up project structure and prepare data files

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create project directory structure: `index.html`, `css/`, `js/`, `data/` | | |
| TASK-002 | Copy `rp-modules-final.json` to `data/` folder | | |
| TASK-003 | Create `data/diplomas.json` with hardcoded module-to-diploma mapping | | |
| TASK-004 | Create `index.html` with Bootstrap 5 CDN links and basic HTML structure | | |
| TASK-005 | Create `css/styles.css` with RP brand color variables and base styles | | |

### Implementation Phase 2: Core UI Components

- GOAL-002: Build the main page layout and search interface

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-006 | Create header with RP logo and navigation | | |
| TASK-007 | Create hero section with search input and search button | | |
| TASK-008 | Create search results container with results count display | | |
| TASK-009 | Create module card template with code, name, description, category, school, rating stars, and external link | | |
| TASK-010 | Create footer with RP branding | | |
| TASK-011 | Create loading animation component (spinner or skeleton) | | |

### Implementation Phase 3: Search Functionality

- GOAL-003: Implement client-side module search and filtering

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-012 | Create `js/data.js` - Load and parse module data from JSON | | |
| TASK-013 | Create `js/search.js` - Implement search filter function (code, name, description, category, school) | | |
| TASK-014 | Create `js/ui.js` - Implement render function to display filtered modules as cards | | |
| TASK-015 | Add event listeners for search input (real-time filtering on keyup) | | |
| TASK-016 | Add event listener for search button click and Enter key | | |
| TASK-017 | Implement "No results found" message when search yields no matches | | |

### Implementation Phase 4: Module Detail View

- GOAL-004: Create module detail modal/section with diploma list

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-018 | Create `js/detail.js` - Module detail modal/section component | | |
| TASK-019 | Create detail view with full module description, code, name, category, school | | |
| TASK-020 | Create diploma list section in detail view | | |
| TASK-021 | Load diploma mapping data and match to current module | | |
| TASK-022 | Display diploma names with links to RP diploma pages | | |
| TASK-023 | Add click handler on module cards to open detail view | | |
| TASK-024 | Add close button/handler for detail view | | |

### Implementation Phase 5: Rating System

- GOAL-005: Implement anonymous 1-5 star rating with LocalStorage persistence

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-025 | Create `js/rating.js` - Rating component with 5 clickable stars | | |
| TASK-026 | Implement LocalStorage read/write for ratings | | |
| TASK-027 | Calculate and store average rating per module | | |
| TASK-028 | Display user's existing rating when opening module detail | | |
| TASK-029 | Display average rating on module cards in search results | | |
| TASK-030 | Handle rating updates (user changes rating) | | |

### Implementation Phase 6: Comment System

- GOAL-006: Implement anonymous commenting with accordion display

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-031 | Create `js/comments.js` - Comment input form and display | | |
| TASK-032 | Implement comment submission with timestamp and optional rating | | |
| TASK-033 | Implement LocalStorage read/write for comments | | |
| TASK-034 | Create accordion/collapsible section for comments display | | |
| TASK-035 | Display comments with timestamp and rating (if provided) | | |
| TASK-036 | Handle empty comments state ("No comments yet") | | |

### Implementation Phase 7: Loading States & Polish

- GOAL-007: Add loading animations and polish UI

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-037 | Implement loading spinner during initial data load | | |
| TASK-038 | Add subtle loading indicator during search filtering | | |
| TASK-039 | Add hover effects on module cards | | |
| TASK-040 | Add transition animations for detail view open/close | | |
| TASK-041 | Test and fix responsive design on mobile, tablet, desktop | | |
| TASK-042 | Cross-browser testing (Chrome, Firefox, Safari, Edge) | | |

## 3. Alternatives

- **ALT-001**: React/Vue framework - Rejected due to constraint CON-001 (Vanilla JS only)
- **ALT-002**: Server-side search - Rejected due to constraint CON-004 (No backend)
- **ALT-003**: IndexedDB for persistence - Rejected as LocalStorage is simpler for this use case
- **ALT-004**: CSS-only accordion - Rejected in favor of Bootstrap JS accordion for better accessibility

## 4. Dependencies

- **DEP-001**: Bootstrap 5.3 CSS/JS via CDN
- **DEP-002**: Google Fonts (optional, for typography)
- **DEP-003**: rp-modules-final.json dataset
- **DEP-004**: Browser LocalStorage API support

## 5. Files

- **FILE-001**: `index.html` - Main HTML page
- **FILE-002**: `css/styles.css` - Custom CSS styles and RP theme
- **FILE-003**: `js/data.js` - Data loading and parsing
- **FILE-004**: `js/search.js` - Search/filter functionality
- **FILE-005**: `js/ui.js` - UI rendering functions
- **FILE-006**: `js/detail.js` - Module detail view component
- **FILE-007**: `js/rating.js` - Star rating system
- **FILE-008**: `js/comments.js` - Comment system
- **FILE-009**: `js/app.js` - Main application initialization
- **FILE-010**: `data/rp-modules-final.json` - Module dataset
- **FILE-011**: `data/diplomas.json` - Diploma mapping data

## 6. Testing

- **TEST-001**: Search returns correct results for module code query (e.g., "A001")
- **TEST-002**: Search returns correct results for module name query (e.g., "biology")
- **TEST-003**: Search returns correct results for description query
- **TEST-004**: Search returns correct results for school query
- **TEST-005**: Module detail shows complete information
- **TEST-006**: Diploma list displays correctly for modules with mapped diplomas
- **TEST-007**: Rating saves to LocalStorage and persists on reload
- **TEST-008**: Average rating calculates correctly
- **TEST-009**: Comment saves to LocalStorage and displays in accordion
- **TEST-010**: Responsive design works at 375px (mobile), 768px (tablet), 1024px+ (desktop)
- **TEST-011**: Loading animation displays during data load
- **TEST-012**: External links open in new tab

## 7. Risks & Assumptions

- **RISK-001**: Large dataset (4000+ modules) may cause slow initial load - Mitigation: Show loading indicator
- **RISK-002**: LocalStorage has 5MB limit - Mitigation: Monitor usage, truncate long comments if needed
- **RISK-003**: Diploma mapping may be incomplete - Mitigation: Show "No diploma information available" for unmapped modules
- **ASSUMPTION-001**: Users have modern browsers with JavaScript and LocalStorage support
- **ASSUMPTION-002**: Bootstrap CDN is accessible
- **ASSUMPTION-003**: Module data is accurate and up-to-date

## 8. Related Specifications / Further Reading

- [ModuleGo Design Specification](../spec/spec-modulego-design.md)
- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.3/)
- [RP Diploma List](https://www.rp.edu.sg/education/diplomas/)
- [RP Module List](https://www.rp.edu.sg/education/modules/)

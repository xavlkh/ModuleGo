---
goal: ModuleGo - Republic Polytechnic Module Viewer Implementation
version: 9.0
date_created: 2026-06-29
last_updated: 2026-07-19
owner: Developer
status: 'In Progress'
tags: ['feature', 'frontend', 'backend', 'vanilla-js', 'tailwindcss', 'glassmorphism', 'flask', 'supabase', 'dark-mode', 'ui-redesign', 'saas-patterns']
---

# Introduction

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

Implementation plan for ModuleGo, a responsive module search application for Republic Polytechnic students. The application uses Vanilla JS, Tailwind CSS (glassmorphism design system), and HTML for the frontend, with Python Flask and Supabase PostgreSQL for the backend. Module data and reviews are stored in Supabase, with Flask proxying all calls so the browser never sees the secret key. SQLite is used only for automated tests.

## 1. Requirements & Constraints

- **REQ-001**: User can enter a search query into an input field
- **REQ-002**: User can submit the query (via pressing Enter)
- **REQ-003**: Search filters modules by Module Code, Module Name, Description, Category, or School
- **REQ-004**: Search results display as a list with Module Code, Name, Description, Category, School
- **REQ-005**: Clicking a module displays a list of diplomas offering that module
- **REQ-006**: Each module entry includes a link to the external RP module page
- **REQ-007**: User can filter modules by School using collapsible filter panel
- **REQ-008**: User can compare two modules side-by-side
- **REQ-009**: User can leave reviews with ratings (1-5) and comments on modules
- **REQ-010**: Reviews are stored in Supabase `reviews` table
- **REQ-011**: User can view existing reviews for each module
- **REQ-012**: User can filter by diploma (populated from `/api/courses`)
- **REQ-013**: User can filter by minimum average rating (5 Stars, 4 Stars & Up, etc.)
- **REQ-014**: User can toggle "Active" filter (modules appearing in at least one diploma)
- **REQ-015**: Filter state persisted in URL params (`q`, `school`, `diploma`, `rating`, `active`, `page`)
- **REQ-B01**: Responsive design works on desktop, tablet, and mobile
- **REQ-B02**: Loading animation displayed during initial data load
- **REQ-B03**: Module comparison page with side-by-side table view
- **REQ-B04**: Collapsible filter panel for school, diploma, rating, and active filters
- **REQ-B05**: Preserve all existing functionality during UI redesign
- **REQ-B06**: Glassmorphism retained ONLY for navbar header; all other surfaces go solid
- **REQ-B07**: Add `Outfit` (Google Fonts) for display headings; keep `Inter` for body
- **REQ-B08**: Remove accent teal — single accent (emerald) only
- **CON-001**: Use only Vanilla JavaScript (no frameworks)
- **CON-002**: Use Tailwind CSS for styling (via CDN) with glassmorphism design tokens
- **CON-003**: Use HTML5 semantic elements
- **CON-004**: Backend uses Python Flask with Supabase PostgreSQL
- **CON-005**: Module data is stored in Supabase, diploma data is served via `/api/courses`
- **CON-006**: No new npm dependencies (Flask + CDN project)
- **GUD-001**: Follow RP brand colors with modern emerald/teal palette
- **GUD-002**: SLP spacing rhythm: hero `py-16 md:py-24`, sections `py-12 md:py-20`, cards `gap-6`
- **GUD-003**: Cards use `bg-white dark:bg-zinc-800` with `shadow-sm`, hover elevates to `shadow-xl`
- **PAT-001**: SLP header pattern: `h-20`, centered nav, logo left
- **PAT-002**: SLP card pattern: solid bg + subtle shadow + hover elevation
- **PAT-003**: SLP footer pattern: multi-column grid with `border-y`

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

### Implementation Phase 9: Supabase Integration

- GOAL-009: Migrate from local SQLite to Supabase for modules and reviews

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-052 | Add `/api/modules` endpoint to query Supabase `rp_modules` table | ✅ | 2026-07-14 |
| TASK-053 | Update Flask to always initialize Supabase client from env vars | ✅ | 2026-07-14 |
| TASK-054 | Update `data.js` to fetch modules from `/api/modules` instead of local JSON | ✅ | 2026-07-14 |
| TASK-055 | Update reviews endpoints to use Supabase (with SQLite fallback for tests) | ✅ | 2026-07-14 |
| TASK-056 | Add school name mapping in `/api/modules` for Supabase data | ✅ | 2026-07-14 |
| TASK-057 | Generate `features` and `suitableFor` fields server-side for comparison | ✅ | 2026-07-14 |
| TASK-058 | Create Supabase migration for reviews foreign key to modules | ✅ | 2026-07-15 |
| TASK-059 | Update `.env.example` with Supabase credential placeholders | ✅ | 2026-07-14 |
| TASK-060 | Verify end-to-end: modules load, search works, reviews save | ✅ | 2026-07-14 |

### Implementation Phase 10: Tailwind CSS Glassmorphism Design System

- GOAL-010: Replace Bootstrap 5 with Tailwind CSS and implement glassmorphism design system

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-061 | Create `app/static/css/app.css` with Tailwind `@theme` config and glassmorphism tokens (colors, shadows, animations) | ✅ | 2026-07-17 |
| TASK-062 | Rewrite `app/templates/base.html` with Tailwind CDN, Inter font, glass navbar, mobile menu, dark footer | ✅ | 2026-07-17 |
| TASK-063 | Rewrite `app/templates/modules/index.html` with gradient hero, glass search bar, glass module cards grid | ✅ | 2026-07-17 |
| TASK-064 | Rewrite `app/templates/modules/comparison.html` with glass comparison panel, gradient VS badge, glass inputs | ✅ | 2026-07-17 |
| TASK-065 | Rewrite `app/templates/modules/reviews.html` with glass stat cards, glass review cards, modern filter toolbar | ✅ | 2026-07-17 |
| TASK-066 | Create custom modal implementation (replaces Bootstrap Modal) with overlay, close-on-escape, close-on-click-outside | ✅ | 2026-07-17 |
| TASK-067 | Update `app/static/js/ui.js` - replace `d-none` with `hidden`, update card HTML to use Tailwind classes | ✅ | 2026-07-17 |
| TASK-068 | Update `app/static/js/detail.js` - replace `bootstrap.Modal` with custom modal, update all Bootstrap classes to Tailwind | ✅ | 2026-07-17 |
| TASK-069 | Update `app/static/js/reviews.js` - replace `bootstrap.Modal` with custom modal, update all Bootstrap classes to Tailwind | ✅ | 2026-07-17 |
| TASK-070 | Update `app/static/js/comparison.js` - replace `d-none` with `hidden`, update Bootstrap classes to Tailwind | ✅ | 2026-07-17 |
| TASK-071 | Delete old `app/static/css/styles.css` (replaced by Tailwind CSS) | ✅ | 2026-07-17 |
| TASK-072 | Verify responsive design across mobile (375px), tablet (768px), and desktop (1024px+) viewports | | |
| TASK-073 | Verify glassmorphism effects render correctly (backdrop-blur, translucent backgrounds, borders) | | |

### Implementation Phase 11: Footer Redesign & Navbar Cleanup

- GOAL-011: Clean up navbar and redesign footer with proper information architecture

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-074 | Remove Diplomas and All Modules external links from navbar (desktop + mobile hamburger) | ✅ | 2026-07-17 |
| TASK-075 | Update footer: add RP Resources links (Diplomas, All Modules), GitHub link, copyright, commit hash | ✅ | 2026-07-17 |
| TASK-076 | Add Flask context processor to inject `current_year` and `commit_hash` into templates | ✅ | 2026-07-17 |
| TASK-077 | Rename "RP Page" button to "Source" on module cards | ✅ | 2026-07-17 |
| TASK-078 | Rename "View on RP Website" to "Source" in module detail modal | ✅ | 2026-07-17 |

### Implementation Phase 12: Dark Mode Design System

- GOAL-012: Implement a comprehensive dark mode with consistent design tokens and good contrast across ALL pages

#### Design System Specification

**Pages to Cover**

| Page | File | Key Components |
|------|------|----------------|
| Home | `index.html` | Hero gradient, search bar (glass-strong), module cards (glass-card), loading spinner, empty state, badges, module detail modal |
| Comparison | `comparison.html` | Hero gradient, comparison panel (glass-card), search inputs, VS badge, comparison table |
| Reviews | `reviews.html` | Hero gradient, stat cards, review list, search/filter inputs, edit review modal |
| All Pages | `base.html` | Navbar (glass-strong), footer (slate-900), theme toggle |

**Color Palette (Dark Mode)**

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `bg-primary` | `white` / `surface-50` | `slate-950` (#0a0f1a) | Page background |
| `bg-secondary` | `surface-100` | `slate-900` (#111827) | Card backgrounds, elevated surfaces |
| `bg-tertiary` | `surface-200` | `slate-800` (#1e293b) | Input fields, dropdowns |
| `text-primary` | `slate-900` | `slate-50` (#f8fafc) | Headlines, primary text |
| `text-secondary` | `slate-600` | `slate-300` (#cbd5e1) | Body text, descriptions |
| `text-tertiary` | `slate-400` | `slate-400` (#94a3b8) | Captions, metadata |
| `border-default` | `slate-200` | `slate-800` | Card borders, dividers |
| `border-strong` | `slate-300` | `slate-700` | Focus rings, active states |
| `accent-primary` | `primary-500` | `primary-400` | Links, CTAs, active states |
| `accent-hover` | `primary-600` | `primary-300` | Hover states |

**Contrast Requirements (WCAG AA)**

| Element | Light Mode Ratio | Dark Mode Ratio | Target |
|---------|-----------------|-----------------|--------|
| Body text on bg | 12.5:1 | 11.2:1 | >= 4.5:1 |
| Secondary text on bg | 7.8:1 | 7.1:1 | >= 4.5:1 |
| Links on bg | 8.2:1 | 6.8:1 | >= 4.5:1 |
| Buttons (text on bg) | 8.5:1 | 7.5:1 | >= 4.5:1 |

**Component Tokens**

| Component | Light | Dark |
|-----------|-------|------|
| Navbar | `glass-strong` (white/85% opacity) | `slate-900/80 + backdrop-blur` |
| Cards | `glass-card` (white/92% opacity) | `slate-900/90 + border-slate-800` |
| Modal | `white gradient` | `slate-900 gradient` |
| Modal Header | `primary-50 gradient` | `primary-900/30 gradient` |
| Footer | `slate-900` (unchanged) | `slate-950` (darker) |
| Input fields | `white/95%` | `slate-800/95%` |
| Select dropdowns | `white` | `slate-800` |
| Hover states | `primary-50 bg` | `slate-800 bg` |
| Stat cards | `white/95%` | `slate-900/95%` |
| Review items | border `slate-100` | border `slate-800` |
| Hero sections | Keep gradient (no change) | Keep gradient (no change) |
| Loading spinner | `primary-100 bg` | `primary-900/30 bg` |
| Empty state | `slate-100 bg` | `slate-800 bg` |
| Badges | `primary-100 bg, primary-700 text` | `primary-900/30 bg, primary-300 text` |
| Alert messages | `amber-50 bg, amber-800 text` | `amber-900/20 bg, amber-200 text` |

**Page-Specific Dark Mode Overrides**

| Page | Component | Light | Dark |
|------|-----------|-------|------|
| Home | Search input | `bg-white/95, text-slate-900, placeholder-slate-400` | `bg-slate-800/95, text-slate-100, placeholder-slate-500` |
| Home | School select | `bg-white/95, text-slate-700` | `bg-slate-800/95, text-slate-200` |
| Home | Module code | `text-primary-600 font-bold` | `text-primary-400 font-bold` |
| Home | Module title | `text-slate-900 font-semibold` | `text-slate-100 font-semibold` |
| Home | Module description | `text-slate-600` | `text-slate-400` |
| Home | School badge | `bg-slate-100, text-slate-700` | `bg-slate-800, text-slate-300` |
| Home | Source link | `text-slate-400 hover:text-primary-500` | `text-slate-500 hover:text-primary-400` |
| Comparison | Search input | `bg-white, border-slate-300, text-slate-900` | `bg-slate-800, border-slate-700, text-slate-100` |
| Comparison | Table header | `bg-primary-50/80, text-primary-800` | `bg-primary-900/20, text-primary-300` |
| Comparison | Table cell | `divide-slate-100` | `divide-slate-800` |
| Comparison | Selected module | `bg-primary-50, border-primary-200` | `bg-primary-900/20, border-primary-800` |
| Reviews | Search input | `bg-white, text-slate-900` | `bg-slate-800, text-slate-100` |
| Reviews | Filter selects | `bg-white, text-slate-700` | `bg-slate-800, text-slate-200` |
| Reviews | Stat card label | `text-slate-500` | `text-slate-400` |
| Reviews | Review comment | `text-slate-600` | `text-slate-400` |
| Reviews | Edit modal textarea | `bg-white, border-slate-300, text-slate-900` | `bg-slate-800, border-slate-700, text-slate-100` |

**Theme Toggle Behavior**

1. Three modes: Light, Dark, System (follows OS preference)
2. Toggle persists to `localStorage`
3. System mode respects `prefers-color-scheme` media query
4. Toggle visible on both desktop (navbar) and mobile (below nav links, not collapsed)
5. Active state: filled background with primary accent color
6. Inactive state: muted text color
7. FOUC prevention: inline script in `<head>` applies theme before body renders

**Implementation Approach**

1. Use Tailwind `darkMode: 'class'` strategy
2. Add `dark` class to `<html>` element via JavaScript
3. Define dark mode overrides in CSS using `.dark` selector for glassmorphism components
4. Use inline `dark:` Tailwind utilities for page-specific overrides
5. Update JS files (`ui.js`, `detail.js`, `comparison.js`, `reviews.js`) to add dark: classes to dynamically generated HTML

**Files to Modify**

| File | Changes |
|------|---------|
| `base.html` | Add theme toggle, dark: classes on navbar/body/footer, FOUC script |
| `app.css` | Add `.dark` overrides for glass, glass-strong, glass-card, buttons, inputs, modals, badges, stat-card, review-item |
| `index.html` | Add dark: classes on search inputs, select, badges, empty state, loading spinner |
| `comparison.html` | Add dark: classes on inputs, table, selected module states, message box |
| `reviews.html` | Add dark: classes on inputs, selects, stat cards, edit modal |
| `ui.js` | Add dark: classes to dynamically generated module card HTML |
| `detail.js` | Add dark: classes to dynamically generated modal content |
| `comparison.js` | Add dark: classes to dynamically generated comparison results and table rows |
| `reviews.js` | Add dark: classes to dynamically generated review items |

**Task List**

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-079 | Define dark mode color tokens and contrast requirements in design system | ✅ | 2026-07-17 |
| TASK-080 | Add `darkMode: 'class'` to Tailwind config | ✅ | 2026-07-17 |
| TASK-081 | Add FOUC prevention script in `<head>` to apply theme before render | ✅ | 2026-07-17 |
| TASK-082 | Create theme toggle component (3 buttons: sun, moon, monitor) in navbar (desktop) | ✅ | 2026-07-17 |
| TASK-083 | Add theme toggle to mobile menu (separate from hamburger, always visible) | ✅ | 2026-07-17 |
| TASK-084 | Implement theme persistence with localStorage | ✅ | 2026-07-17 |
| TASK-085 | Add system preference detection and `prefers-color-scheme` listener | ✅ | 2026-07-17 |
| TASK-086 | Add dark mode overrides for glass components in CSS (glass, glass-strong, glass-card) | ✅ | 2026-07-17 |
| TASK-087 | Add dark mode overrides for buttons in CSS (btn-primary-glow, btn-outline-glass) | ✅ | 2026-07-17 |
| TASK-088 | Add dark mode overrides for inputs in CSS (input-glass, select) | ✅ | 2026-07-17 |
| TASK-089 | Add dark mode overrides for modals in CSS (modal-panel, modal-header) | ✅ | 2026-07-17 |
| TASK-090 | Add dark mode overrides for badges, stat cards, review items in CSS | ✅ | 2026-07-17 |
| TASK-091 | Update `base.html` - add dark: classes on navbar, body, footer | ✅ | 2026-07-17 |
| TASK-092 | Update `index.html` - add dark: classes on search inputs, select, badges, empty state | ✅ | 2026-07-17 |
| TASK-093 | Update `comparison.html` - add dark: classes on inputs, table, message box | ✅ | 2026-07-17 |
| TASK-094 | Update `reviews.html` - add dark: classes on inputs, selects, stat cards, edit modal | ✅ | 2026-07-17 |
| TASK-095 | Update `ui.js` - add dark: classes to dynamically generated module card HTML | ✅ | 2026-07-17 |
| TASK-096 | Update `detail.js` - add dark: classes to dynamically generated modal content | ✅ | 2026-07-17 |
| TASK-097 | Update `comparison.js` - add dark: classes to comparison results and table rows | ✅ | 2026-07-17 |
| TASK-098 | Update `reviews.js` - add dark: classes to dynamically generated review items | ✅ | 2026-07-17 |
| TASK-099 | Test all pages in dark mode (Home, Comparison, Reviews) | ✅ | 2026-07-17 |
| TASK-100 | Verify contrast ratios with WebAIM Contrast Checker | ✅ | 2026-07-17 |
| TASK-101 | Verify theme toggle works on mobile (separate from hamburger menu) | ✅ | 2026-07-17 |
| TASK-102 | Test system preference detection and automatic switching | ✅ | 2026-07-17 |

### Implementation Phase 13: Pagination

- GOAL-013: Add client-side pagination to home page with 9 modules per page

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-103 | Add pagination state properties (`currentPage`, `perPage = 9`, `filteredModules`) to UIRenderer in `ui.js` | ✅ | 2026-07-17 |
| TASK-104 | Add `renderPaginatedResults(modules)` method that slices modules for current page | ✅ | 2026-07-17 |
| TASK-105 | Add `renderPagination(totalPages)` with prev/next buttons and page numbers | ✅ | 2026-07-17 |
| TASK-106 | Add `goToPage(page)` that updates currentPage and re-renders | ✅ | 2026-07-17 |
| TASK-107 | Update `handleSearch` to store filteredModules, reset page, call renderPaginatedResults | ✅ | 2026-07-17 |
| TASK-108 | Add `<div id="paginationContainer">` to `index.html` | ✅ | 2026-07-17 |

### Implementation Phase 14: Pagination Best Practices (Ellipsis, A11y, Orientation)

- GOAL-014: Upgrade pagination with ellipsis logic, accessibility, and results info

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-109 | Replace `getPageNumbers()` with proper ellipsis (anchor page 1, show last page, current ±1 window, `'...'` for gaps) | ✅ | 2026-07-18 |
| TASK-110 | Add "Page X of Y" text inside `renderPagination()` | ✅ | 2026-07-18 |
| TASK-111 | Add `renderResultsInfo(total)` method with "Showing X–Y of Z modules" | ✅ | 2026-07-18 |
| TASK-112 | Add `keydown` listener for Left/Right arrow keys on pagination nav | ✅ | 2026-07-18 |
| TASK-113 | Add `<div id="paginationAnnouncer" aria-live="polite">` to `index.html` | ✅ | 2026-07-18 |
| TASK-114 | Update `goToPage()` to set screen reader announcer text | ✅ | 2026-07-18 |

### Implementation Phase 15: Codebase Refactor (Merge JS, Repository Pattern, Macros)

- GOAL-015: Simplify JS from 8 files to 4, add repository pattern in app.py, extract shared Jinja macros

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-115 | Add `parseTimestamp()`, `showMessage()`, `createReviewActionsHTML()`, `createModalController()` to `utils.js` | ✅ | 2026-07-17 |
| TASK-116 | Merge `search.js` into `ui.js` | ✅ | 2026-07-17 |
| TASK-117 | Merge `app.js` into `ui.js` as `UIRenderer.initApp()` | ✅ | 2026-07-17 |
| TASK-118 | Merge `detail.js` review CRUD into `reviews.js` | ✅ | 2026-07-17 |
| TASK-119 | Update all HTML templates' script tags to reflect merged files | ✅ | 2026-07-17 |
| TASK-120 | Remove `generate-comparison-fields.js` | ✅ | 2026-07-17 |
| TASK-121 | Remove proxy methods (`escapeHtml`, `createStars`) from JS files | ✅ | 2026-07-17 |
| TASK-122 | Create `ReviewRepository` class in `app.py` | ✅ | 2026-07-17 |
| TASK-123 | Refactor all 6 review route handlers to use `ReviewRepository` | ✅ | 2026-07-17 |
| TASK-124 | Create `app/templates/_macros.html` with Jinja macros | ✅ | 2026-07-17 |
| TASK-125 | Refactor all templates to use Jinja macros | ✅ | 2026-07-17 |
| TASK-126 | Add `.select-chevron` class to `app.css` | ✅ | 2026-07-17 |
| TASK-127 | Add `@functools.lru_cache` with TTL to `get_modules()` | ✅ | 2026-07-17 |

### Implementation Phase 16: Diploma Data Scraping

- GOAL-016: Create live scraper for RP diploma pages, yielding structured JSON + CSV for Supabase import

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-128 | Create `app/static/local-data/scripts/step4_scrape_diplomas.py` — scrapes listing page for diploma links + metadata | | |
| TASK-129 | Implement detail page extraction of curriculum modules by category (general, discipline, elective) | | |
| TASK-130 | Handle conditional paths: split into separate diploma entries with suffixed codes (e.g. R57-BUS, R57-HOS) | | |
| TASK-131 | Output `rp_diplomas.json` (nested JSON) and `rp_diplomas.csv` (flat CSV) | | |
| TASK-132 | Define Supabase `rp_diplomas` and `diploma_modules` table schemas | | |

### Implementation Phase 17: Design Tokens & Typography

- GOAL-017: Update Tailwind config and CSS custom properties for the new visual language

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-133 | In `app/templates/base.html`: add Google Fonts `<link>` for `Outfit` (weights 600-800) alongside Inter | | |
| TASK-134 | In `app/templates/base.html`: update `tailwind.config` — change `fontFamily.display` to `['Outfit', ...]`, add `fontFamily.body` as `['Inter', ...]`. Replace `surface` scale with `zinc` references. Remove `accent` color scale entirely | | |
| TASK-135 | In `app/static/css/app.css`: update `:root` block — add `--font-display: "Outfit"`, `--font-body: "Inter"`. Remove accent-300/400/500 tokens. Update `--color-primary-*` to slightly desaturated values (reduce chroma from 0.2 to 0.16 on primary-500) | | |
| TASK-136 | In `app/static/css/app.css`: update body `font-family` to `var(--font-body)`. Add utility class `.font-display` mapping to `var(--font-display)` | | |

### Implementation Phase 18: Surface & Color System

- GOAL-018: Replace glassmorphism with solid surfaces; migrate from slate to zinc

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-137 | In `app/templates/base.html`: change body classes from `bg-slate-50 dark:bg-slate-950` to `bg-zinc-50 dark:bg-zinc-950` | | |
| TASK-138 | In `app/static/css/app.css`: replace custom `--dark-*` vars with zinc-based values: `--dark-bg: oklch(0.14 0.008 260)`, `--dark-bg-elevated: oklch(0.17 0.008 260)`, `--dark-border: oklch(0.23 0.006 260)`, `--dark-border-subtle: oklch(0.26 0.006 260)`, `--dark-text: oklch(0.92 0.005 260)`, `--dark-text-muted: oklch(0.6 0.005 260)` | | |
| TASK-139 | In `app/static/css/app.css`: rewrite `.glass-card` to solid surface — `background: white`, `border: 1px solid oklch(0.92 0.005 260)`, remove `backdrop-filter`. Dark variant: `background: var(--dark-bg-elevated)`, `border-color: var(--dark-border)` | | |
| TASK-140 | In `app/static/css/app.css`: keep `.glass` and `.glass-strong` ONLY for navbar. Add comment documenting this constraint | | |
| TASK-141 | In `app/static/css/app.css`: rewrite `.stat-card` to solid: `background: white`, remove `backdrop-filter`. Dark: `background: var(--dark-bg-elevated)` | | |
| TASK-142 | In `app/static/css/app.css`: rewrite `.modal-panel` — light: `background: white`, dark: `background: var(--dark-bg)`. Remove gradient backgrounds | | |
| TASK-143 | In `app/static/css/app.css`: rewrite `.modal-header` — light: `background: oklch(0.97 0.02 155)`, dark: `background: oklch(0.2 0.03 155)`. Remove backdrop-blur | | |

### Implementation Phase 19: Hero Section Redesign

- GOAL-019: Replace gradient hero with clean minimal hero matching SLP pattern

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-144 | In `app/templates/_macros.html`: rewrite `hero()` macro — remove gradient bg, use `bg-zinc-50 dark:bg-zinc-950` (transparent to page bg). Add `py-16 md:py-24` padding. Headline: `font-display font-bold text-4xl md:text-5xl lg:text-6xl tracking-tight text-zinc-900 dark:text-white`. Remove SVG dot overlay | | |
| TASK-145 | In `app/templates/modules/index.html`: update hero call — add description text "Search through Republic Polytechnic's 537 modules, compare courses, and read student reviews" | | |

### Implementation Phase 20: Component Restyling

- GOAL-020: Restyle all interactive components to match SLP patterns

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-146 | In `app/static/css/app.css`: rewrite `.btn-primary` — remove gradient, use solid `background: var(--color-primary-500)`, `border-radius: 0.75rem`, no border. Hover: `background: var(--color-primary-600)`, `transform: translateY(-1px)`, `box-shadow: 0 4px 12px oklch(0.66 0.16 149 / 0.3)`. Dark: same but `primary-600` base | | |
| TASK-147 | In `app/static/css/app.css`: rewrite `.btn-outline` — `background: white`, `border: 1px solid zinc-200`, `color: zinc-700`. Hover: `background: zinc-50`. Dark: `bg-zinc-800`, `border-zinc-700`, `text-zinc-200` | | |
| TASK-148 | In `app/static/css/app.css`: rewrite `.input-field` — `background: white`, `border: 1px solid oklch(0.9 0.005 260)`, `border-radius: 0.75rem`. Remove `backdrop-filter`. Dark: `bg-zinc-900`, `border-zinc-800` | | |
| TASK-149 | In `app/static/css/app.css`: update `.select-field` to match input-field styling (solid bg, no blur) | | |
| TASK-150 | In `app/static/css/app.css`: update `.badge` — `background: oklch(0.97 0.02 155)`, `color: oklch(0.49 0.15 150)`, `border: 1px solid oklch(0.89 0.09 155 / 0.5)`. Dark: `bg oklch(0.2 0.02 150)`, `text oklch(0.85 0.08 150)` | | |
| TASK-151 | In `app/static/css/app.css`: update `.review-item` — `border-bottom: 1px solid oklch(0.92 0.005 260)` | | |
| TASK-152 | In `app/static/js/ui.js`: update module card HTML generation — replace `glass-card` class with new solid card class. Keep existing content structure | | |

### Implementation Phase 21: Header & Footer

- GOAL-021: Redesign header to SLP pattern; expand footer

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-153 | In `app/templates/base.html`: update header — height `h-20` (from `h-16`). Add `border-b border-zinc-200 dark:border-zinc-800` bottom border. Background: keep glass-strong for light, use `bg-zinc-900/90` for dark | | |
| TASK-154 | In `app/templates/base.html`: update logo — use `font-display font-bold` on "ModuleGo" text. Keep the emerald icon box | | |
| TASK-155 | In `app/templates/_macros.html`: update `navLinks()` — use `font-display font-semibold text-[15px]`, active state: `text-zinc-900 dark:text-white underline underline-offset-4`, hover: `text-zinc-600 dark:text-zinc-300`. Remove icon from nav links (cleaner) | | |
| TASK-156 | In `app/templates/base.html`: rewrite footer to 3-column grid — col 1: logo + tagline, col 2: quick links (Home, Comparison, Reviews), col 3: data source + GitHub. Use `bg-zinc-50 dark:bg-zinc-950` (same as page bg), `border-t border-zinc-200 dark:border-zinc-800`. Padding: `py-12` | | |

### Implementation Phase 22: Page-Specific Updates

- GOAL-022: Update comparison and reviews pages to match new design system

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-157 | In `app/templates/modules/comparison.html`: update hero call to use new hero macro. Ensure comparison panel uses solid card styling (not glass) | | |
| TASK-158 | In `app/templates/modules/reviews.html`: update hero call. Ensure stat cards use new `.stat-card` solid styling. Ensure review cards use solid bg | | |
| TASK-159 | In `app/static/js/comparison.js`: update module card HTML generation — replace `glass-card` class with new solid card class. Keep existing content structure | | |

### Implementation Phase 23: Dark Mode Polish

- GOAL-023: Ensure dark mode parity across all components

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-160 | Audit all `.dark` CSS rules in `app/static/css/app.css` — ensure every component has proper dark variant using updated zinc-based vars | | |
| TASK-161 | In `app/templates/base.html`: ensure footer dark mode uses `bg-zinc-950` not `bg-slate-950` | | |
| TASK-162 | Test theme toggle in browser — verify FOUC prevention script still works, light/dark/system all render correctly | | |

### Implementation Phase 24: Verification

- GOAL-024: Verify all pages render correctly in both modes

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-163 | Visual check: home page light mode — hero, search bar, module cards, pagination, footer | | |
| TASK-164 | Visual check: home page dark mode — same components, verify contrast | | |
| TASK-165 | Visual check: comparison page light + dark — dual search, VS badge, comparison table | | |
| TASK-166 | Visual check: reviews page light + dark — stats, filter toolbar, review cards | | |
| TASK-167 | Functional check: search, filter, sort, pagination, detail modal, review CRUD all work | | |
| TASK-168 | Mobile check: responsive layout at 375px, 768px, 1024px viewports | | |

## 3. Alternatives

- **ALT-001**: React/Vue framework - Rejected due to constraint CON-001 (Vanilla JS only)
- **ALT-002**: LocalStorage for review persistence - Rejected in favor of Supabase for better data integrity and shared access
- **ALT-003**: IndexedDB for persistence - Rejected as Supabase provides better querying and cross-device access
- **ALT-004**: Bootstrap 5 + Tailwind hybrid - Rejected to avoid CSS bloat and maintain clean utility-only approach
- **ALT-005**: Separate rating and comment systems - Rejected in favor of unified review system
- **ALT-006**: Self-hosted PostgreSQL - Rejected in favor of managed Supabase for simplicity
- **ALT-007**: Bootstrap Modal with Tailwind CSS - Rejected in favor of fully custom modal to eliminate Bootstrap JS dependency
- **ALT-008**: Keep glassmorphism but tone it down - Rejected because the SLP pattern of solid surfaces is cleaner and more maintainable. Glassmorphism on cards fights with content hierarchy
- **ALT-009**: Switch to a different accent color (blue, rose) - Rejected because emerald is RP's brand color and already established in the codebase
- **ALT-010**: Use a CSS framework like shadcn/ui - Rejected because this is a Flask + Jinja project with no React. The existing Tailwind CDN approach works fine
- **ALT-011**: Add GSAP scroll animations - Rejected as out of scope. The redesign is visual-only; motion can be added later

## 4. Dependencies

- **DEP-001**: Tailwind CSS v3 via CDN (runtime CSS generation)
- **DEP-002**: Inter font via Google Fonts CDN
- **DEP-003**: Lucide Icons via CDN (icon library)
- **DEP-004**: Supabase `rp_modules` table (module dataset)
- **DEP-005**: Supabase `reviews` table (review storage)
- **DEP-006**: Flask 3.1.3 (Python web framework)
- **DEP-007**: supabase 2.31.0 (Python client)
- **DEP-008**: python-dotenv 1.2.2 (env var loading)
- **DEP-009**: Python 3.12+ runtime
- **DEP-010**: Supabase `rp_courses` table (diploma data from scraping)
- **DEP-011**: `app/static/local-data/scripts/` — Python scraping scripts (requests, BeautifulSoup, agent-browser)
- **DEP-012**: Outfit font via Google Fonts CDN (display headings)

## 5. Files

| Path | Description |
|------|-------------|
| `app/templates/modules/index.html` | Main search and browse page with collapsible filter panel |
| `app/templates/modules/comparison.html` | Module comparison page (Tailwind glassmorphism) |
| `app/templates/modules/reviews.html` | Review dashboard page (Tailwind glassmorphism) |
| `app/templates/base.html` | Layout template with glass navbar/footer (Tailwind) |
| `app/templates/_macros.html` | Shared Jinja macros (hero, navLinks, themeToggle, selectField) |
| `app/static/css/app.css` | Tailwind CSS with `:root` custom properties and glassmorphism tokens |
| `app/static/js/utils.js` | Shared utilities (escapeHtml, createStars, parseTimestamp, showMessage, createReviewActionsHTML, createModalController) |
| `app/static/js/data.js` | Data loading from `/api/modules` + `/api/courses` with diploma/rating/active filtering |
| `app/static/js/ui.js` | UI rendering, search, pagination, filter panel + app initialization (merged from search.js + app.js) |
| `app/static/js/comparison.js` | Module comparison logic (Tailwind markup) |
| `app/static/js/reviews.js` | Review dashboard + module detail review CRUD (merged from detail.js) |
| `app/static/local-data/scripts/` | Python scraping scripts (step1_get_tokens, step2_scrape_all_modules, step3_generate_comparison, step4_scrape_diplomas) |
| `app/static/local-data/data/` | Scraping output (gitignored) — tokens.json, rp_modules_synopsis, rp_modules_comparison, rp_diplomas_curriculum |
| `app/static/local-data/SCRAPING_GUIDE.md` | Documentation for module scraping pipeline |
| `app.py` | Flask backend with Supabase integration + ReviewRepository |
| `tests/test_reviews.py` | Pytest test suite for review API endpoints |
| `requirements.txt` | Python dependencies |
| `.env.example` | Supabase credential template |
| `vercel.json` | Vercel serverless function configuration |

## 6. Testing

- **TEST-001**: Search returns correct results for module code query (e.g., "A001")
- **TEST-002**: Search returns correct results for module name query (e.g., "biology")
- **TEST-003**: Search returns correct results for description query
- **TEST-004**: School filter correctly filters modules by selected school
- **TEST-005**: Module detail shows complete information
- **TEST-006**: Diploma list displays correctly for modules with mapped diplomas
- **TEST-007**: Review submission saves to Supabase via Flask API
- **TEST-008**: Reviews display correctly with rating and timestamp
- **TEST-009**: Module comparison page loads and displays two modules side-by-side
- **TEST-010**: Responsive design works at 375px (mobile), 768px (tablet), 1024px+ (desktop)
- **TEST-011**: Loading animation displays during data load
- **TEST-012**: External links open in new tab
- **TEST-013**: Flask backend starts and serves API endpoints correctly
- **TEST-014**: `/api/modules` returns JSON array of modules from Supabase
- **TEST-015**: SQLite fallback works for automated tests (no Supabase needed)
- **TEST-016**: Pagination shows 9 modules per page, resets on search/filter change
- **TEST-017**: Ellipsis shows page 1 anchored when beyond page 3
- **TEST-018**: Arrow keys navigate pages when pagination focused
- **TEST-019**: Screen reader announces page changes via aria-live
- **TEST-020**: All pytest tests pass after JS merge refactor
- **TEST-021**: Run `python app/static/local-data/scripts/step4_scrape_diplomas.py` — ~44 diploma entries output
- **TEST-022**: Visual regression — compare before/after screenshots of all 3 pages in light and dark mode
- **TEST-023**: Contrast audit — verify WCAG AA (4.5:1) for all text against backgrounds in both modes
- **TEST-024**: Functional regression — run `pytest tests/` to ensure no API or security tests break
- **TEST-025**: Mobile responsive — verify no horizontal scroll or layout breaks at 375px width
- **TEST-026**: Theme toggle — verify FOUC prevention, system preference detection, and manual toggle all work

## 7. Risks & Assumptions

- **RISK-001**: Large dataset (537 modules) may cause slow initial load - Mitigation: Show loading indicator
- **RISK-002**: Supabase outage would affect both module data and reviews - Mitigation: Acceptable for student project; SQLite fallback for tests
- **RISK-003**: Diploma mapping may be incomplete - Mitigation: Show "No diploma information available" for unmapped modules
- **RISK-004**: Flask backend must be running for all functionality - Mitigation: Show error message if server not available
- **RISK-005**: Supabase column names may differ from expectations - Mitigation: Map columns in `/api/modules` endpoint
- **RISK-006**: Tailwind CDN adds runtime CSS generation - Mitigation: Acceptable for student project scale; can migrate to build step later
- **RISK-007**: Glassmorphism effects may not render on older browsers - Mitigation: Graceful degradation with fallback solid backgrounds
- **RISK-008**: Dark mode contrast may be insufficient on certain components - Mitigation: Test all combinations with contrast checker, minimum 4.5:1 ratio
- **RISK-009**: Theme toggle may flash on page load (FOUC) - Mitigation: Inline script in `<head>` to apply theme before render
- **RISK-010**: Merging detail.js into reviews.js may cause regression in detail modal - Mitigation: Test coverage of review CRUD
- **RISK-011**: Changing CSS class names on cards may break JS that targets `.glass-card` — verify `ui.js` and `detail.js` selectors
- **RISK-012**: Dark mode custom oklch vars may produce unexpected contrast on some monitors — test on multiple screens
- **ASSUMPTION-001**: Users have modern browsers with JavaScript support
- **ASSUMPTION-002**: Tailwind CSS CDN and Google Fonts CDN are accessible
- **ASSUMPTION-003**: Module data in Supabase is accurate and up-to-date
- **ASSUMPTION-004**: Python 3.12+ is installed on the server
- **ASSUMPTION-005**: Supabase credentials in `.env` are valid

## 8. Related Specifications / Further Reading

- [ModuleGo Design Specification](./spec-modulego-design.md)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Tailwind CSS Theme Variables](https://tailwindcss.com/docs/theme)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [RP Diploma List](https://www.rp.edu.sg/education/diplomas/)
- [RP Module List](https://www.rp.edu.sg/education/modules/)
- [RP Module Synopsis (OutSystems)](https://lcs.rp.edu.sg/RPModuleSynopsis/)
- [Scraping Guide](../app/static/local-data/SCRAPING_GUIDE.md)
- [SaaS Landing Page Reference](https://saaslandingpage.com/)
- [oklch Color Picker](https://oklch.com/)

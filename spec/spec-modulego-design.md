---
title: ModuleGo - Republic Polytechnic Module Viewer Design Specification
version: 1.0
date_created: 2026-06-29
owner: Developer
tags: ['design', 'frontend', 'vanilla-js', 'bootstrap']
---

# Introduction

ModuleGo is a responsive web application that allows Republic Polytechnic students to search for modules, view module details, and discover which diplomas offer each module. The application addresses the limitation of the official RP Module viewer by providing a more intuitive and comprehensive module exploration experience.

## 1. Purpose & Scope

**Purpose:** Define the design system, UI components, and interaction patterns for the ModuleGo application.

**Scope:** Frontend web application built with Vanilla JS, CSS/Bootstrap, and HTML. No backend required.

**Audience:** Republic Polytechnic students seeking to explore modules and their associated diplomas.

**Assumptions:**
- Module data is provided via static JSON file (`rp-modules-final.json`)
- Diploma-to-module mapping will be hardcoded
- All data persistence uses browser LocalStorage

## 2. Definitions

| Term | Definition |
|------|------------|
| Module | A course unit offered at Republic Polytechnic, identified by a module code (e.g., A001) |
| Diploma | A full-time program of study at RP (e.g., Diploma in Applied AI & Analytics) |
| School | Academic division at RP (e.g., School of Infocomm) |
| Client-side filtering | Searching/filtering data in the browser without server requests |
| LocalStorage | Web API for storing key-value pairs in the browser |

## 3. Requirements, Constraints & Guidelines

### Core Requirements

- **REQ-001**: User can enter a search query into an input field
- **REQ-002**: User can submit the query (via typing, pressing Enter, or clicking search button)
- **REQ-003**: Search filters modules by Module Code, Module Name, Description, Category, or School
- **REQ-004**: Search results display as a list showing Module Code, Module Name, Description, Category, and School
- **REQ-005**: Clicking a module displays a list of diplomas offering that module
- **REQ-006**: Each module entry includes a link to the external RP module page (url field)

### Bonus Requirements

- **REQ-B01**: Responsive design works on desktop, tablet, and mobile viewports
- **REQ-B02**: Loading animation displayed during initial data load
- **REQ-B03**: Anonymous commenting system on module detail pages
- **REQ-B04**: Anonymous 1-5 star rating system on module detail pages
- **REQ-B05**: Average module rating displayed on search results page
- **REQ-B06**: Comments displayed in accordion/collapsible section

### Constraints

- **CON-001**: Use only Vanilla JavaScript (no frameworks like React, Vue, Angular)
- **CON-002**: Use Bootstrap 5 for styling and responsive grid
- **CON-003**: Use HTML5 semantic elements
- **CON-004**: No backend/server required
- **CON-005**: Data persistence via browser LocalStorage only

### Design Guidelines

- **GUD-001**: Follow RP brand colors: Green (#00A651), Black (#1a1a1a), White (#ffffff)
- **GUD-002**: Use Bootstrap 5 grid system (12-column)
- **GUD-003**: Maintain WCAG AA contrast ratios for accessibility
- **GUD-004**: Mobile-first responsive approach
- **GUD-005**: Clean, functional UI prioritizing information hierarchy

## 4. Interfaces & Data Contracts

### Module Data Schema (from rp-modules-final.json)

```json
{
  "code": "string (e.g., 'A001')",
  "name": "string (e.g., '3D Printing Hacks')",
  "description": "string (module description text)",
  "category": "string (e.g., 'Science', or empty)",
  "school": "string (e.g., 'School of Applied Science')",
  "url": "string (URL to RP module page)",
  "source": "string (data source identifier)"
}
```

### Diploma Mapping Schema (to be created)

```json
{
  "A001": ["Diploma in Mechatronics", "Diploma in Engineering"],
  "A103": ["Diploma in Biomedical Science", "Diploma in Sports Science"]
}
```

### Rating/Comment Schema (LocalStorage)

```json
{
  "A001": {
    "ratings": [5, 4, 3, 5, 4],
    "average": 4.2,
    "comments": [
      {
        "id": "timestamp",
        "text": "Great module!",
        "rating": 5,
        "timestamp": "2026-06-29T14:00:00Z"
      }
    ]
  }
}
```

### Page Structure

```
index.html (Home/Search Page)
├── Header (Logo, Navigation)
├── Hero Section (Search Input)
├── Search Results Section
│   ├── Results Count
│   └── Module Cards List
│       ├── Module Code
│       ├── Module Name
│       ├── Description (truncated)
│       ├── Category Badge
│       ├── School
│       ├── Average Rating (stars)
│       └── External Link Button
├── Module Detail Modal/Section
│   ├── Full Module Details
│   ├── Diploma List
│   ├── Rating Component (1-5 stars)
│   └── Comments Accordion
└── Footer
```

## 5. Acceptance Criteria

### Search Functionality
- **AC-001**: Given user is on the home page, When user types in search input, Then matching modules appear in real-time
- **AC-002**: Given user types "A001", When search filters, Then only modules with code containing "A001" are shown
- **AC-003**: Given user types "biology", When search filters, Then modules with "biology" in name or description are shown
- **AC-004**: Given no results match, When search is performed, Then "No modules found" message is displayed

### Module Display
- **AC-005**: Given search results are displayed, When user views the list, Then each module shows code, name, description, category, and school
- **AC-006**: Given module has a URL, When user views module card, Then external link button is visible and clickable

### Module Detail
- **AC-007**: Given user clicks a module, When detail view opens, Then full description and diploma list are displayed
- **AC-008**: Given module has diplomas, When detail view opens, Then diploma names are listed with links to diploma pages

### Rating System
- **AC-009**: Given user is on module detail, When user clicks star, Then rating is saved to LocalStorage
- **AC-010**: Given user has rated, When page reloads, Then user's rating is remembered
- **AC-011**: Given multiple ratings exist, When module card displays, Then average rating is shown

### Comment System
- **AC-012**: Given user is on module detail, When user submits comment, Then comment is saved to LocalStorage
- **AC-013**: Given comments exist, When user expands accordion, Then comments are displayed with timestamp
- **AC-014**: Given user submits comment with rating, When saved, Then both comment and rating are stored

### Responsive Design
- **AC-015**: Given user is on mobile (< 768px), When viewing search results, Then modules display in single column
- **AC-016**: Given user is on tablet (768px-1024px), When viewing search results, Then modules display in 2 columns
- **AC-017**: Given user is on desktop (> 1024px), When viewing search results, Then modules display in 3 columns

### Loading States
- **AC-018**: Given page is loading, When data is being fetched, Then loading animation is displayed
- **AC-019**: Given search is filtering, When results are updating, Then subtle loading indicator is shown

## 6. Test Automation Strategy

- **Test Levels**: Manual testing, browser developer tools
- **Frameworks**: None required (vanilla JS)
- **Test Data Management**: Use provided rp-modules-final.json
- **Coverage Requirements**: All user stories tested manually
- **Performance Testing**: Test with full dataset, ensure smooth filtering

## 7. Rationale & Context

**Design Decisions:**
1. **Bootstrap 5**: Rapid development, built-in responsive grid, consistent components
2. **Client-side filtering**: No server needed, instant search feedback, works offline
3. **LocalStorage**: Simple persistence without backend, suitable for anonymous ratings
4. **Accordion for comments**: Keeps module detail clean, allows progressive disclosure
5. **Green theme**: Matches RP brand identity for institutional familiarity

**Trade-offs:**
- LocalStorage data is browser-specific and can be cleared
- No user authentication means ratings are anonymous and not verifiable
- Client-side filtering requires loading entire dataset upfront

## 8. Dependencies & External Integrations

### Data Dependencies
- **DAT-001**: `rp-modules-final.json` - Module dataset provided locally
- **DAT-002**: Hardcoded diploma mapping - Module-to-diploma relationships

### External Links
- **EXT-001**: RP Module Pages - Links to official module information
- **EXT-002**: RP Diploma Pages - Links to diploma program pages

### Infrastructure Dependencies
- **INF-001**: Modern web browser with JavaScript and LocalStorage support
- **INF-002**: Bootstrap 5 CSS/JS via CDN

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

- [ ] All user stories implemented and functional
- [ ] Search filters correctly across all module fields
- [ ] Module detail shows complete information and diploma list
- [ ] Rating system saves and retrieves from LocalStorage
- [ ] Comment system saves and displays correctly
- [ ] Responsive design works on mobile, tablet, and desktop
- [ ] Loading animations display during data operations
- [ ] External links open in new tabs
- [ ] No JavaScript errors in browser console
- [ ] Bootstrap CDN loads correctly

## 11. Related Specifications / Further Reading

- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.3/)
- [RP Diploma List](https://www.rp.edu.sg/education/diplomas/)
- [RP Module List](https://www.rp.edu.sg/education/modules/)
- [RP Updated Modules](https://lcs.rp.edu.sg/RPModuleSynopsis/)

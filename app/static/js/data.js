/**
 * Handles module data loading, lookup, and search.
 * @module data
 */
/**
 * Centralised data layer for modules, diplomas, and ratings.
 * All data is loaded once from the Flask API and kept in memory for
 * client-side search and filtering.
 * @module data
 */
const DataManager = {
    /** @type {Array<Object>} All module objects from /api/modules */
    modules: [],
    /** @type {Array<Object>} All diploma/course objects from /api/courses */
    diplomas: [],
    /** @type {Object<string, {average_rating: number|null, review_count: number}>} Rating summaries keyed by module code */
    ratings: {},
    /** @type {boolean} True after the first successful loadData() call */
    loaded: false,

    /**
     * Fetch modules, courses, and ratings from the Flask API in parallel.
     * Populates this.modules, this.diplomas, and this.ratings.
     * @returns {Promise<Array<Object>>} The loaded modules array.
     * @throws {Error} If module or course fetch fails.
     */
    async loadData() {
        try {
            const [moduleResponse, courseResponse, ratingResponse] = await Promise.all([
                fetch('/api/modules'),
                fetch('/api/courses'),
                fetch('/api/ratings')
            ]);

            if (!moduleResponse.ok || !courseResponse.ok) {
                throw new Error('Failed to load module catalogue data.');
            }

            this.modules = await moduleResponse.json();
            this.diplomas = await courseResponse.json();
            this.ratings = ratingResponse.ok ? await ratingResponse.json() : {};

            this.loaded = true;

            return this.modules;
        } catch (error) {
            console.error('Error loading data:', error);
            throw error;
        }
    },

    /**
     * Look up a single module by its code (case-insensitive).
     * @param {string} code - The module code to find.
     * @returns {Object|undefined} The matching module, or undefined.
     */
    getModule(code) {
        const lookupCode = (code || '').toLowerCase();
        return this.modules.find(m => (m.code || '').toLowerCase() === lookupCode);
    },

    /**
     * Get the rating summary for a module code.
     * @param {string} moduleCode - The module code (case-insensitive).
     * @returns {{average_rating: number|null, review_count: number}} Rating summary.
     */
    getRatingSummary(moduleCode) {
        return this.ratings[(moduleCode || '').toUpperCase()] || {
            average_rating: null,
            review_count: 0
        };
    },

    /**
     * Re-fetch rating summaries from the API (e.g. after a review mutation).
     * @returns {Promise<Object>} Updated ratings map.
     */
    async refreshRatingSummaries() {
        const response = await fetch('/api/ratings');
        if (!response.ok) {
            throw new Error('Failed to refresh rating summaries.');
        }

        this.ratings = await response.json();
        return this.ratings;
    },

    /**
     * Find all diplomas that include a given module code.
     * Searches general, major, discipline, elective, and industry module lists.
     * @param {string} moduleCode - The module code to look up.
     * @returns {Array<Object>} Diploma objects with an added `category` field.
     */
    getDiplomasByModule(moduleCode) {
        if (!moduleCode) {
            return [];
        }

        const code = moduleCode.toUpperCase();
        const categories = [
            { key: 'general_modules', label: 'General' },
            { key: 'major_modules', label: 'Major' },
            { key: 'discipline_modules', label: 'Discipline' },
            { key: 'elective_modules', label: 'Elective' },
            { key: 'industry_modules', label: 'Industry' }
        ];

        const results = [];
        for (const course of this.diplomas) {
            for (const cat of categories) {
                const arr = course[cat.key];
                if (Array.isArray(arr) && arr.some(m => (typeof m === 'string' ? m : m.code) === code)) {
                    results.push({ ...course, category: cat.label });
                    break;
                }
            }
        }
        return results;
    },

    /**
     * Search modules by query string with weighted relevance scoring.
     * Matches against code, name, school, synopsis, summary, suitableFor, and url.
     * Lower score = higher relevance (scores start at 100 and decrease).
     * @param {string} query - The search query.
     * @returns {Array<Object>} Matching modules sorted by relevance.
     */
    searchModules(query) {
        if (!query || query.trim() === '') {
            return this.modules;
        }

        const searchTerm = this.normalizeSearchText(query);
        const searchTokens = searchTerm.split(' ').filter(Boolean);
        const results = [];

        for (const module of this.modules) {
            const code = this.normalizeSearchText(module.code);
            const name = this.normalizeSearchText(module.name);
            const school = this.normalizeSearchText(module.school);
            const searchableText = this.normalizeSearchText([
                module.code,
                module.name,
                module.school,
                module.synopsis,
                module.summary,
                module.suitableFor,
                module.url
            ].filter(Boolean).join(' '));

            if (!searchTokens.every(token => searchableText.includes(token))) {
                continue;
            }

            let score = 100;

            if (code === searchTerm) score -= 80;
            else if (code.startsWith(searchTerm)) score -= 60;
            else if (code.includes(searchTerm)) score -= 45;

            if (name === searchTerm) score -= 55;
            else if (name.startsWith(searchTerm)) score -= 40;
            else if (name.includes(searchTerm)) score -= 25;

            if (school.includes(searchTerm)) score -= 12;
            score += Math.max(0, searchTokens.length - 1) * 3;

            results.push({ module, score });
        }

        results.sort((a, b) => {
            if (a.score !== b.score) return a.score - b.score;
            return (a.module.code || '').localeCompare(b.module.code || '');
        });

        return results.map(r => r.module);
    },

    /**
     * Get a deduplicated, sorted list of all diplomas for the filter dropdown.
     * @returns {Array<{code: string, name: string}>} Sorted diploma list.
     */
    getDiplomaList() {
        const seen = new Set();
        const list = [];
        for (const course of this.diplomas) {
            if (!seen.has(course.course_code)) {
                seen.add(course.course_code);
                list.push({ code: course.course_code, name: course.course_name });
            }
        }
        list.sort((a, b) => a.name.localeCompare(b.name));
        return list;
    },

    /**
     * Apply diploma, rating, and active filters to a module list.
     * @param {Array<Object>} modules - The modules to filter.
     * @param {Object} [filters={}] - Filter criteria.
     * @param {string} [filters.diploma] - Course code to filter by, or 'all'.
     * @param {string} [filters.rating] - Minimum average rating, or 'all'.
     * @param {string} [filters.active] - 'true' to show only active modules.
     * @returns {Array<Object>} Filtered modules.
     */
    filterModules(modules, filters = {}) {
        let results = modules ? [...modules] : [...this.modules];
        const { diploma, rating, active } = filters;

        if (diploma && diploma !== 'all') {
            const course = this.diplomas.find(c => c.course_code === diploma);
            if (course) {
                const codes = new Set();
                for (const key of ['general_modules', 'major_modules', 'discipline_modules', 'elective_modules', 'industry_modules']) {
                    const arr = course[key];
                    if (Array.isArray(arr)) {
                        for (const m of arr) {
                            codes.add(typeof m === 'string' ? m : m.code);
                        }
                    }
                }
                results = results.filter(m => codes.has(m.code));
            }
        }

        if (rating && rating !== 'all') {
            const min = parseInt(rating, 10);
            results = results.filter(m => {
                const s = this.getRatingSummary(m.code);
                return s.review_count > 0 && s.average_rating !== null && s.average_rating >= min;
            });
        }

        if (active === 'true') {
            results = results.filter(m => this.getDiplomasByModule(m.code).length > 0);
        }

        return results;
    },

    /**
     * Normalise text for search: lowercase, replace non-alphanumeric with spaces, trim.
     * @param {*} value - The value to normalise.
     * @returns {string} Normalised search text.
     */
    normalizeSearchText(value) {
        return String(value || '')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, ' ')
            .trim();
    }
};

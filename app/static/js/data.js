/**
 * Handles module data loading, lookup, and search.
 * @module data
 */
const DataManager = {
    modules: [],
    diplomas: [],
    ratings: {},
    loaded: false,

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

    getModule(code) {
        const lookupCode = (code || '').toLowerCase();
        return this.modules.find(m => (m.code || '').toLowerCase() === lookupCode);
    },

    getRatingSummary(moduleCode) {
        return this.ratings[(moduleCode || '').toUpperCase()] || {
            average_rating: null,
            review_count: 0
        };
    },

    async refreshRatingSummaries() {
        const response = await fetch('/api/ratings');
        if (!response.ok) {
            throw new Error('Failed to refresh rating summaries.');
        }

        this.ratings = await response.json();
        return this.ratings;
    },

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

    normalizeSearchText(value) {
        return String(value || '')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, ' ')
            .trim();
    }
};

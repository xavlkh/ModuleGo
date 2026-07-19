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
        results.sort((a, b) =>
        (a.course_code || '').localeCompare(b.course_code || '')
    );
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

    normalizeSearchText(value) {
        return String(value || '')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, ' ')
            .trim();
    }
};

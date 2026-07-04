// Handles module data loading, lookup, and search.
const DataManager = {
    modules: [],
    diplomas: [],
    loaded: false,

    async loadData() {
        try {
            // Load module records from the local JSON file.
            const moduleResponse = await fetch('/static/data/rp-modules-final.json');
            this.modules = await moduleResponse.json();

            // Load diploma data
            const diplomaResponse = await fetch('/static/data/diploma.json');
            this.diplomas = await diplomaResponse.json();

            this.loaded = true;

            return this.modules;
        } catch (error) {
            console.error('Error loading data:', error);
            throw error;
        }
    },

    getModule(code) {
        // Match module codes case-insensitively.
        const lookupCode = (code || '').toLowerCase();
        return this.modules.find(m => (m.code || '').toLowerCase() === lookupCode);
    },

    getDiplomasByModule(moduleCode) {
        if (!moduleCode) {
            return [];
        }

        const code = moduleCode.toUpperCase();

        return this.diplomas.filter(diploma => {
            if (!Array.isArray(diploma.modules)) {
                return false;
            }

            return diploma.modules.includes(code);
        });
    },

    searchModules(query) {
        if (!query || query.trim() === '') {
            return this.modules;
        }

        // Split the search into simple keyword tokens.
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
                module.category,
                module.description,
                module.features,
                module.suitableFor,
                module.source
            ].filter(Boolean).join(' '));

            // Require every keyword to appear somewhere in the module.
            if (!searchTokens.every(token => searchableText.includes(token))) {
                continue;
            }

            let score = 100;

            // Rank exact code and title matches higher.
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
        // Normalize punctuation and spacing for easier matching.
        return String(value || '')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, ' ')
            .trim();
    }
};

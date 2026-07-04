const DataManager = {
    modules: [],
    diplomas: [],
    loaded: false,

    async loadData() {
        try {
            // Load module data
            const moduleResponse = await fetch('data/rp-modules-final.json');
            this.modules = await moduleResponse.json();

            // Load diploma data
            const diplomaResponse = await fetch('data/diploma.json');
            this.diplomas = await diplomaResponse.json();

            this.loaded = true;

            return this.modules;
        } catch (error) {
            console.error('Error loading data:', error);
            throw error;
        }
    },

    getModule(code) {
        return this.modules.find(m => m.code === code);
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

        const searchTerm = query.toLowerCase().trim();

        const results = [];

        for (const module of this.modules) {
            const code = (module.code || '').toLowerCase();
            const name = (module.name || '').toLowerCase();
            const description = (module.description || '').toLowerCase();
            const school = (module.school || '').toLowerCase();

            if (code.includes(searchTerm)) {
                results.push({ module, priority: 1 });
            } else if (name.includes(searchTerm)) {
                results.push({ module, priority: 2 });
            } else if (school.includes(searchTerm)) {
                results.push({ module, priority: 3 });
            } else if (description.includes(searchTerm)) {
                results.push({ module, priority: 4 });
            }
        }

        results.sort((a, b) => a.priority - b.priority);

        return results.map(r => r.module);
    }
};
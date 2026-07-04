// Connects the search box to the result list.
const SearchManager = {
    currentQuery: '',
    debounceTimer: null,
    searchRunId: 0,

    init() {
        // Bind search input, Enter key, and button click.
        const searchInput = document.getElementById('searchInput');
        const searchBtn = document.getElementById('searchBtn');

        searchInput.addEventListener('input', (e) => {
            this.handleInput(e.target.value);
        });

        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleSearch(e.target.value);
            }
        });

        searchBtn.addEventListener('click', () => {
            this.handleSearch(searchInput.value);
        });
    },

    handleInput(value) {
        // Wait briefly so search does not run on every keystroke.
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.handleSearch(value);
        }, 300);
    },

    handleSearch(query) {
        clearTimeout(this.debounceTimer);
        this.currentQuery = query;
        // Ignore older delayed searches.
        const runId = ++this.searchRunId;
        
        UIRenderer.showLoading();
        
        setTimeout(() => {
            if (runId !== this.searchRunId) return;

            if (!DataManager.loaded) {
                UIRenderer.renderResults([]);
                UIRenderer.updateResultsCount(0);
                return;
            }

            const results = DataManager.searchModules(query);
            UIRenderer.renderResults(results);
            UIRenderer.updateResultsCount(results.length);
        }, 150);
    }
};

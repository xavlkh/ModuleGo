const SearchManager = {
    currentQuery: '',
    debounceTimer: null,

    init() {
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
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.handleSearch(value);
        }, 300);
    },

    handleSearch(query) {
        this.currentQuery = query;
        
        UIRenderer.showLoading();
        
        setTimeout(() => {
            const results = DataManager.searchModules(query);
            UIRenderer.renderResults(results);
            UIRenderer.updateResultsCount(results.length);
        }, 150);
    }
};

const SearchManager = {
    currentQuery: '',
    debounceTimer: null,

    init() {
        const searchInput = document.getElementById('searchInput');
        const searchBtn = document.getElementById('searchBtn');
        const schoolFilter = document.getElementById('schoolFilter');

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
        if (schoolFilter) {
    schoolFilter.addEventListener('change', () => {
      this.handleSearch(searchInput.value);
    });
  }
    },

    handleInput(value) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.handleSearch(value);
        }, 300);
    },

    handleSearch(query) {
        this.currentQuery = query;
        const schoolFilter = document.getElementById('schoolFilter');
        const selectedSchool = schoolFilter ? schoolFilter.value : 'all';

        UIRenderer.showLoading();
        
        setTimeout(() => {
            let results = DataManager.searchModules(query);
            if (selectedSchool !== 'all') {
      results = results.filter(module => module.school === selectedSchool);
    }
            UIRenderer.renderResults(results);
            UIRenderer.updateResultsCount(results.length);
        }, 150);
          
    }
};

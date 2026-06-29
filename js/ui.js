const UIRenderer = {
    resultsContainer: null,
    loadingSpinner: null,
    noResults: null,
    resultsCount: null,
    moduleCount: null,

    init() {
        this.resultsContainer = document.getElementById('resultsContainer');
        this.loadingSpinner = document.getElementById('loadingSpinner');
        this.noResults = document.getElementById('noResults');
        this.resultsCount = document.getElementById('resultsCount');
        this.moduleCount = document.getElementById('moduleCount');
    },

    showLoading() {
        this.resultsContainer.innerHTML = '';
        this.loadingSpinner.classList.remove('d-none');
        this.noResults.classList.add('d-none');
    },

    hideLoading() {
        this.loadingSpinner.classList.add('d-none');
    },

    renderResults(modules) {
        this.hideLoading();
        this.resultsContainer.innerHTML = '';

        if (modules.length === 0) {
            this.noResults.classList.remove('d-none');
            return;
        }

        this.noResults.classList.add('d-none');

        modules.forEach(module => {
            const card = this.createModuleCard(module);
            this.resultsContainer.appendChild(card);
        });
    },

    createModuleCard(module) {
        const col = document.createElement('div');
        col.className = 'col-12 col-md-6 col-lg-4';

        const truncatedDesc = this.truncateText(module.description, 150);

        col.innerHTML = `
            <div class="module-card" data-code="${module.code}">
                <div class="module-code">${module.code}</div>
                <div class="module-name">${module.name}</div>
                <div class="module-description">${truncatedDesc}</div>
                <div class="module-meta">
                    <span class="badge bg-secondary">${module.school}</span>
                </div>
                <div class="card-actions">
                    <button class="btn btn-sm btn-outline-primary view-details-btn" data-code="${module.code}">
                        <i class="bi bi-info-circle me-1"></i>View Details
                    </button>
                    <a href="${module.url}" target="_blank" class="btn btn-sm btn-outline-secondary" onclick="event.stopPropagation()">
                        <i class="bi bi-box-arrow-up-right me-1"></i>RP Page
                    </a>
                </div>
            </div>
        `;

        const card = col.querySelector('.module-card');
        card.addEventListener('click', () => {
            DetailManager.showModuleDetail(module.code);
        });

        return col;
    },

    updateResultsCount(count) {
        this.resultsCount.textContent = `${count} module${count !== 1 ? 's' : ''}`;
    },

    updateModuleCount(count) {
        this.moduleCount.textContent = count;
    },

    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength).trim() + '...';
    }
};

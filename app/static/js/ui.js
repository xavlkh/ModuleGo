/**
 * Home page: UI rendering, search, and app initialization.
 * @module ui
 */
const UIRenderer = {
    resultsContainer: null,
    loadingSpinner: null,
    noResults: null,
    resultsCount: null,
    paginationContainer: null,
    resultsInfo: null,
    paginationAnnouncer: null,
    currentQuery: '',
    debounceTimer: null,
    searchRunId: 0,
    currentPage: 1,
    perPage: 9,
    filteredModules: [],

    init() {
        this.resultsContainer = document.getElementById('resultsContainer');
        this.loadingSpinner = document.getElementById('loadingSpinner');
        this.noResults = document.getElementById('noResults');
        this.resultsCount = document.getElementById('resultsCount');
        this.paginationContainer = document.getElementById('paginationContainer');
        this.resultsInfo = document.getElementById('resultsInfo');
        this.paginationAnnouncer = document.getElementById('paginationAnnouncer');
        this.initSearch();
        this.initKeyboardNav();
    },

    initSearch() {
        const searchInput = document.getElementById('searchInput');
        const searchBtn = document.getElementById('searchBtn');
        const schoolFilter = document.getElementById('schoolFilter');

        searchInput.addEventListener('input', (e) => this.handleInput(e.target.value));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch(e.target.value);
        });
        searchBtn.addEventListener('click', () => this.handleSearch(searchInput.value));
        if (schoolFilter) {
            schoolFilter.addEventListener('change', () => this.handleSearch(searchInput.value));
        }
    },

    initKeyboardNav() {
        document.addEventListener('keydown', (e) => {
            if (!this.paginationContainer || this.paginationContainer.classList.contains('hidden')) return;
            const active = document.activeElement;
            if (!active || !this.paginationContainer.contains(active)) return;
            if (e.key === 'ArrowLeft' && this.currentPage > 1) {
                e.preventDefault();
                this.goToPage(this.currentPage - 1);
            } else if (e.key === 'ArrowRight') {
                const totalPages = Math.ceil(this.filteredModules.length / this.perPage);
                if (this.currentPage < totalPages) {
                    e.preventDefault();
                    this.goToPage(this.currentPage + 1);
                }
            }
        });
    },

    handleInput(value) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => this.handleSearch(value), 300);
    },

    handleSearch(query) {
        clearTimeout(this.debounceTimer);
        this.currentQuery = query;
        // Monotonically increasing run ID kills stale setTimeout callbacks,
        // preventing a fast typist from seeing flash of wrong results.
        const runId = ++this.searchRunId;
        const schoolFilter = document.getElementById('schoolFilter');
        const selectedSchool = schoolFilter ? schoolFilter.value : 'all';

        this.showLoading();

        setTimeout(() => {
            if (runId !== this.searchRunId) return;
            if (!DataManager.loaded) {
                this.renderPaginatedResults([]);
                this.updateResultsCount(0);
                return;
            }

            let results = DataManager.searchModules(query);
            if (selectedSchool !== 'all') {
                results = results.filter(m => m.school === selectedSchool);
            }
            this.currentPage = 1;
            this.filteredModules = results;
            this.renderPaginatedResults(results);
            this.updateResultsCount(results.length);
        }, 150);
    },

    showLoading() {
        this.resultsContainer.innerHTML = '';
        this.loadingSpinner.classList.remove('hidden');
        this.noResults.classList.add('hidden');
    },

    hideLoading() {
        this.loadingSpinner.classList.add('hidden');
    },

    renderResults(modules) {
        this.hideLoading();
        this.resultsContainer.innerHTML = '';
        if (modules.length === 0) {
            this.noResults.classList.remove('hidden');
            return;
        }
        this.noResults.classList.add('hidden');
        modules.forEach(m => this.resultsContainer.appendChild(this.createModuleCard(m)));
        lucide.createIcons();
    },

    renderPaginatedResults(modules) {
        this.hideLoading();
        this.filteredModules = modules;
        const totalPages = Math.ceil(modules.length / this.perPage);
        if (this.currentPage > totalPages) this.currentPage = totalPages || 1;
        const start = (this.currentPage - 1) * this.perPage;
        const pageModules = modules.slice(start, start + this.perPage);
        this.renderResults(pageModules);
        this.renderResultsInfo(modules.length);
        this.renderPagination(totalPages);
    },

    renderPagination(totalPages) {
        if (!this.paginationContainer) return;
        this.paginationContainer.innerHTML = '';
        if (totalPages <= 1) {
            this.paginationContainer.classList.add('hidden');
            return;
        }
        this.paginationContainer.classList.remove('hidden');

        const nav = document.createElement('nav');
        nav.setAttribute('aria-label', 'Pagination');
        nav.className = 'inline-flex items-center gap-1';

        const btnBase = 'inline-flex items-center justify-center rounded-lg text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-primary-400/40';
        const btnIdle = 'w-9 h-9 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/60';
        const btnDisabled = 'w-9 h-9 text-slate-300 dark:text-slate-600 cursor-not-allowed pointer-events-none';
        const btnActive = 'w-9 h-9 bg-primary-500 text-white shadow-sm';

        const prevBtn = document.createElement('button');
        prevBtn.className = `${btnBase} ${btnIdle.replace('w-9 h-9', 'w-8 h-8')} ${this.currentPage === 1 ? btnDisabled : ''}`;
        prevBtn.innerHTML = '<i data-lucide="chevron-left" class="w-4 h-4"></i>';
        prevBtn.setAttribute('aria-label', 'Previous page');
        if (this.currentPage > 1) {
            prevBtn.addEventListener('click', () => this.goToPage(this.currentPage - 1));
        }
        nav.appendChild(prevBtn);

        const pages = this.getPageNumbers(this.currentPage, totalPages);
        pages.forEach(p => {
            if (p === '...') {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'w-9 h-9 inline-flex items-center justify-center text-slate-300 dark:text-slate-600 select-none text-sm';
                ellipsis.textContent = '\u2026';
                ellipsis.setAttribute('aria-hidden', 'true');
                nav.appendChild(ellipsis);
            } else {
                const pageBtn = document.createElement('button');
                pageBtn.className = `${btnBase} ${p === this.currentPage ? btnActive : btnIdle}`;
                pageBtn.textContent = p;
                pageBtn.setAttribute('aria-label', `Page ${p}`);
                if (p === this.currentPage) {
                    pageBtn.setAttribute('aria-current', 'page');
                }
                pageBtn.addEventListener('click', () => this.goToPage(p));
                nav.appendChild(pageBtn);
            }
        });

        const nextBtn = document.createElement('button');
        nextBtn.className = `${btnBase} ${btnIdle.replace('w-9 h-9', 'w-8 h-8')} ${this.currentPage === totalPages ? btnDisabled : ''}`;
        nextBtn.innerHTML = '<i data-lucide="chevron-right" class="w-4 h-4"></i>';
        nextBtn.setAttribute('aria-label', 'Next page');
        if (this.currentPage < totalPages) {
            nextBtn.addEventListener('click', () => this.goToPage(this.currentPage + 1));
        }
        nav.appendChild(nextBtn);

        this.paginationContainer.appendChild(nav);
        lucide.createIcons();
    },

    getPageNumbers(current, total) {
        if (total <= 7) {
            return Array.from({ length: total }, (_, i) => i + 1);
        }

        const pages = [1];
        const showLeftEllipsis = current > 3;
        const showRightEllipsis = current < total - 2;

        if (showLeftEllipsis) pages.push('...');

        const windowStart = Math.max(2, current - 1);
        const windowEnd = Math.min(total - 1, current + 1);
        for (let i = windowStart; i <= windowEnd; i++) {
            pages.push(i);
        }

        if (showRightEllipsis) pages.push('...');
        pages.push(total);
        return pages;
    },

    goToPage(page) {
        this.currentPage = page;
        this.renderPaginatedResults(this.filteredModules);
        this.resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        const totalPages = Math.ceil(this.filteredModules.length / this.perPage);
        if (this.paginationAnnouncer) {
            this.paginationAnnouncer.textContent = `Page ${page} of ${totalPages}`;
        }
    },

    renderResultsInfo(total) {
        if (!this.resultsInfo) return;
        if (total === 0) {
            this.resultsInfo.textContent = '';
            return;
        }
        const start = (this.currentPage - 1) * this.perPage + 1;
        const end = Math.min(this.currentPage * this.perPage, total);
        const totalPages = Math.ceil(total / this.perPage);
        this.resultsInfo.textContent = `${start}\u2013${end} of ${total} modules \u00b7 Page ${this.currentPage} of ${totalPages}`;
    },

    createModuleCard(module) {
        const col = document.createElement('div');
        col.className = 'col-span-1';
        const truncatedDesc = this.truncateText(module.synopsis, 150);
        const school = module.school || 'School not listed';
        const url = module.url || '#';

        col.innerHTML = `
            <div class="glass-card p-5 h-full flex flex-col cursor-pointer group" data-code="${module.code}">
                <div class="text-xs font-bold uppercase tracking-wider text-primary-500 dark:text-primary-400 mb-1.5">${module.code}</div>
                <h3 class="text-base font-bold text-slate-900 dark:text-white mb-2 leading-snug group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">${escapeHtml(module.name)}</h3>
                <p class="text-sm text-slate-500 dark:text-slate-400 mb-3 flex-1 line-clamp-3">${truncatedDesc}</p>
                <div class="mb-3">
                    <span class="inline-flex items-center rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-600 dark:text-slate-300">${school}</span>
                </div>
                <div class="flex items-center gap-1 text-sm text-amber-600 dark:text-amber-400 mb-3" data-rating-code="${module.code}">
                    ${this.createRatingMarkup(module.code)}
                </div>
                <div class="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-700/50">
                    <button class="btn-outline text-xs py-1.5 px-3 view-details-btn" data-code="${module.code}">
                        <i data-lucide="info" class="w-3.5 h-3.5 mr-1 inline-block"></i>View Details
                    </button>
                    <a href="${url}" target="_blank" class="text-xs text-slate-400 dark:text-slate-400 hover:text-primary-500 dark:hover:text-primary-400 transition-colors px-2 py-1" onclick="event.stopPropagation()">
                        <i data-lucide="external-link" class="w-3.5 h-3.5 mr-1 inline-block"></i>Source
                    </a>
                </div>
            </div>
        `;
        col.querySelector('.glass-card').addEventListener('click', () => DetailManager.showModuleDetail(module.code));
        return col;
    },

    createRatingMarkup(moduleCode) {
        const summary = DataManager.getRatingSummary(moduleCode);
        if (!summary.review_count) {
            return `<i data-lucide="star" class="w-4 h-4 inline-block" aria-hidden="true"></i><span class="text-slate-400 dark:text-slate-400">No reviews yet</span>`;
        }
        const label = summary.review_count === 1 ? 'review' : 'reviews';
        return `
            <i data-lucide="star" class="w-4 h-4 inline-block fill-amber-400 text-amber-400" aria-hidden="true"></i>
            <span class="font-semibold">${Number(summary.average_rating).toFixed(1)}</span>
            <span class="text-slate-400 dark:text-slate-400">(${summary.review_count} ${label})</span>
        `;
    },

    updateRatingDisplay(moduleCode) {
        const el = document.querySelector(`[data-rating-code="${moduleCode}"]`);
        if (el) {
            el.innerHTML = this.createRatingMarkup(moduleCode);
            lucide.createIcons();
        }
    },

    updateResultsCount(count) {
        this.resultsCount.textContent = `${count} module${count !== 1 ? 's' : ''}`;
    },

    truncateText(text, maxLength) {
        if (!text) return '';
        // Synopses are often a single sentence — end at the first period when
        // it fits within the limit rather than cutting mid-word.
        const dotIndex = text.indexOf('.');
        if (dotIndex !== -1 && dotIndex + 1 <= maxLength) {
            return text.substring(0, dotIndex + 1);
        }
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength).trim() + '...';
    }
};

async function initHomePage() {
    try {
        UIRenderer.init();
        DetailManager.init();
        UIRenderer.showLoading();
        await DataManager.loadData();
        UIRenderer.filteredModules = DataManager.modules;
        UIRenderer.renderPaginatedResults(DataManager.modules);
        UIRenderer.updateResultsCount(DataManager.modules.length);
    } catch (error) {
        console.error('Failed to initialize app:', error);
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) spinner.classList.add('hidden');
        document.getElementById('resultsContainer').innerHTML = `
            <div class="col-span-full py-16 text-center">
                <div class="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50 dark:bg-red-900/30 mb-4">
                    <i data-lucide="triangle-alert" class="w-8 h-8 text-red-500 dark:text-red-400"></i>
                </div>
                <h3 class="text-xl font-semibold text-slate-700 dark:text-slate-200 mb-1">Failed to load module data</h3>
                <p class="text-slate-500 dark:text-slate-400">Please refresh the page or try again later.</p>
            </div>
        `;
        lucide.createIcons();
    }
}

document.addEventListener('DOMContentLoaded', () => initHomePage());

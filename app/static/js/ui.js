/**
 * Home page: UI rendering, search, pagination, and app initialisation.
 * @module ui
 */

/** CSS class strings for the Active/All toggle button. */
const ACTIVE_BTN_CLASSES = {
    inactive: 'w-28 bg-white/95 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-xl py-3 text-sm font-semibold text-zinc-700 dark:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-all duration-200 shrink-0',
    active: 'w-28 bg-zinc-200 dark:bg-zinc-700 border border-zinc-300 dark:border-zinc-600 rounded-xl py-3 text-sm font-semibold text-zinc-900 dark:text-white hover:bg-zinc-300 dark:hover:bg-zinc-600 transition-all duration-200 shrink-0',
};

const UIRenderer = {
    resultsContainer: null,
    loadingSpinner: null,
    noResults: null,
    resultsCount: null,
    paginationContainer: null,
    resultsInfo: null,
    paginationAnnouncer: null,
    searchInput: null,
    schoolFilter: null,
    diplomaFilter: null,
    ratingFilter: null,
    activeFilter: null,
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
        this.searchInput = document.getElementById('searchInput');
        const filterToggle = document.getElementById('filterToggle');
        const filterPanel = document.getElementById('filterPanel');
        this.schoolFilter = document.getElementById('schoolFilter');
        this.diplomaFilter = document.getElementById('diplomaFilter');
        this.ratingFilter = document.getElementById('ratingFilter');
        this.activeFilter = document.getElementById('activeFilter');

        this.searchInput.addEventListener('input', (e) => this.handleInput(e.target.value));
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch(e.target.value);
        });

        if (filterToggle && filterPanel) {
            filterToggle.addEventListener('click', () => {
                const isClosed = filterPanel.style.gridTemplateRows === '0fr';
                filterPanel.style.gridTemplateRows = isClosed ? '1fr' : '0fr';
                const chevron = document.getElementById('filterChevron');
                if (chevron) chevron.style.transform = isClosed ? 'rotate(180deg)' : 'rotate(0deg)';
            });
        }

        const triggerSearch = () => this.handleSearch(this.searchInput.value);
        if (this.schoolFilter) this.schoolFilter.addEventListener('change', triggerSearch);
        if (this.diplomaFilter) this.diplomaFilter.addEventListener('change', triggerSearch);
        if (this.ratingFilter) this.ratingFilter.addEventListener('change', triggerSearch);

        if (this.activeFilter) {
            this.activeFilter.addEventListener('click', () => {
                const isActive = this.activeFilter.dataset.active === 'true';
                this.activeFilter.dataset.active = isActive ? 'false' : 'true';
                this.activeFilter.className = isActive ? ACTIVE_BTN_CLASSES.inactive : ACTIVE_BTN_CLASSES.active;
                const label = this.activeFilter.querySelector('span');
                if (label) label.textContent = isActive ? 'All' : 'Active';
                triggerSearch();
            });
        }

        const clearFilters = document.getElementById('clearFilters');
        if (clearFilters) {
            clearFilters.addEventListener('click', () => {
                if (this.schoolFilter) this.schoolFilter.value = 'all';
                if (this.diplomaFilter) this.diplomaFilter.value = 'all';
                if (this.ratingFilter) this.ratingFilter.value = 'all';
                if (this.activeFilter) {
                    this.activeFilter.dataset.active = 'false';
                    this.activeFilter.className = ACTIVE_BTN_CLASSES.inactive;
                    const label = this.activeFilter.querySelector('span');
                    if (label) label.textContent = 'All';
                }
                this.searchInput.value = '';
                triggerSearch();
            });
        }
    },

    populateDiplomaFilter() {
        if (!this.diplomaFilter) return;
        DataManager.getDiplomaList().forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.code;
            opt.textContent = d.name;
            this.diplomaFilter.appendChild(opt);
        });
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

    handleSearch(query, page = 1) {
        clearTimeout(this.debounceTimer);
        this.currentQuery = query;

        const selectedSchool = this.schoolFilter ? this.schoolFilter.value : 'all';
        const selectedDiploma = this.diplomaFilter ? this.diplomaFilter.value : 'all';
        const selectedRating = this.ratingFilter ? this.ratingFilter.value : 'all';
        const selectedActive = this.activeFilter ? this.activeFilter.dataset.active : 'false';

        const url = new URL(window.location);
        url.searchParams.delete('bookmarks');
        const setParam = (key, value) => {
            if (value && value !== 'all' && value !== 'false') url.searchParams.set(key, value);
            else url.searchParams.delete(key);
        };
        setParam('q', query);
        setParam('school', selectedSchool);
        setParam('diploma', selectedDiploma);
        setParam('rating', selectedRating);
        if (selectedActive === 'true') url.searchParams.set('active', 'true');
        else url.searchParams.delete('active');
        if (page > 1) url.searchParams.set('page', page);
        else url.searchParams.delete('page');
        window.history.replaceState({}, '', url);

        const runId = ++this.searchRunId;
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
            results = DataManager.filterModules(results, {
                diploma: selectedDiploma,
                rating: selectedRating,
                active: selectedActive,
            });
            this.currentPage = page;
            this.filteredModules = results;
            window.currentFilteredModules = results; // #5 - EXPOSE FOR EXPORT
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
    },

    renderPaginatedResults(modules) {
        this.hideLoading();
        this.filteredModules = modules;
        window.currentFilteredModules = modules; // #5 - EXPOSE FOR EXPORT
        const totalPages = Math.ceil(modules.length / this.perPage);
        if (this.currentPage > totalPages) this.currentPage = totalPages || 1;
        const start = (this.currentPage - 1) * this.perPage;
        const pageModules = modules.slice(start, start + this.perPage);
        this.renderResults(pageModules);
        this.renderResultsInfo(modules.length);
        this.renderPagination(totalPages);
        lucide.createIcons();
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
        const btnIdle = 'w-9 h-9 text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-700/60';
        const btnDisabled = 'w-9 h-9 text-zinc-300 dark:text-zinc-600 cursor-not-allowed pointer-events-none';
        const btnActive = 'w-9 h-9 bg-primary-500 text-white shadow-sm';

        const prevBtn = document.createElement('button');
        prevBtn.className = `${btnBase} ${btnIdle.replace('w-9 h-9', 'w-8 h-8')} ${this.currentPage === 1 ? btnDisabled : ''}`;
        prevBtn.innerHTML = '<i data-lucide="chevron-left" class="w-4 h-4"></i>';
        prevBtn.setAttribute('aria-label', 'Previous page');
        if (this.currentPage > 1) prevBtn.addEventListener('click', () => this.goToPage(this.currentPage - 1));
        nav.appendChild(prevBtn);

        this.getPageNumbers(this.currentPage, totalPages).forEach(p => {
            if (p === '...') {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'w-9 h-9 inline-flex items-center justify-center text-zinc-300 dark:text-zinc-600 select-none text-sm';
                ellipsis.textContent = '\u2026';
                ellipsis.setAttribute('aria-hidden', 'true');
                nav.appendChild(ellipsis);
            } else {
                const pageBtn = document.createElement('button');
                pageBtn.className = `${btnBase} ${p === this.currentPage ? btnActive : btnIdle}`;
                pageBtn.textContent = p;
                pageBtn.setAttribute('aria-label', `Page ${p}`);
                if (p === this.currentPage) pageBtn.setAttribute('aria-current', 'page');
                pageBtn.addEventListener('click', () => this.goToPage(p));
                nav.appendChild(pageBtn);
            }
        });

        const nextBtn = document.createElement('button');
        nextBtn.className = `${btnBase} ${btnIdle.replace('w-9 h-9', 'w-8 h-8')} ${this.currentPage === totalPages ? btnDisabled : ''}`;
        nextBtn.innerHTML = '<i data-lucide="chevron-right" class="w-4 h-4"></i>';
        nextBtn.setAttribute('aria-label', 'Next page');
        if (this.currentPage < totalPages) nextBtn.addEventListener('click', () => this.goToPage(this.currentPage + 1));
        nav.appendChild(nextBtn);

        this.paginationContainer.appendChild(nav);
    },

    getPageNumbers(current, total) {
        if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
        const pages = [1];
        if (current > 3) pages.push('...');
        const start = Math.max(2, current - 1);
        const end = Math.min(total - 1, current + 1);
        for (let i = start; i <= end; i++) pages.push(i);
        if (current < total - 2) pages.push('...');
        pages.push(total);
        return pages;
    },

    goToPage(page) {
        this.currentPage = page;
        this.renderPaginatedResults(this.filteredModules);
        const url = new URL(window.location);
        if (page > 1) url.searchParams.set('page', page);
        else url.searchParams.delete('page');
        window.history.replaceState({}, '', url);
        if (this.paginationAnnouncer) {
            this.paginationAnnouncer.textContent = `Page ${page} of ${Math.ceil(this.filteredModules.length / this.perPage)}`;
        }
    },

    renderResultsInfo(total) {
        if (!this.resultsInfo) return;
        if (total === 0) { this.resultsInfo.textContent = ''; return; }
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
            <div class="glass-card p-5 h-full flex flex-col cursor-pointer group" data-code="${escapeHtml(module.code)}">
                <div class="text-xs font-bold uppercase tracking-wider text-primary-500 dark:text-primary-400 mb-1.5">${escapeHtml(module.code)}</div>
                <h3 class="text-base font-bold text-zinc-900 dark:text-white mb-2 leading-snug group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">${escapeHtml(module.name)}</h3>
                <p class="text-sm text-zinc-500 dark:text-zinc-400 mb-3 flex-1 line-clamp-3">${escapeHtml(truncatedDesc)}</p>
                <div class="mb-3">
                    <span class="inline-flex items-center rounded-full bg-zinc-100 dark:bg-zinc-800 px-2.5 py-1 text-xs font-medium text-zinc-600 dark:text-zinc-300">${escapeHtml(school)}</span>
                </div>
                <div class="flex items-center gap-1 text-sm text-amber-600 dark:text-amber-400 mb-3" data-rating-code="${escapeHtml(module.code)}">
                    ${this.createRatingMarkup(module.code)}
                </div>
                <div class="flex items-center justify-between pt-3 border-t border-zinc-100 dark:border-zinc-700/50">
                    <button class="btn-outline text-xs py-1.5 px-3 view-details-btn" data-code="${escapeHtml(module.code)}">
                        <i data-lucide="info" class="w-3.5 h-3.5 mr-1 inline-block"></i>View Details
                    </button>
                    <a href="${escapeHtml(url)}" target="_blank" class="text-xs text-zinc-400 dark:text-zinc-400 hover:text-primary-500 dark:hover:text-primary-400 transition-colors px-2 py-1" onclick="event.stopPropagation()">
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
            return '<i data-lucide="star" class="w-4 h-4 inline-block" aria-hidden="true"></i><span class="text-zinc-400 dark:text-zinc-400">No reviews yet</span>';
        }
        const label = summary.review_count === 1 ? 'review' : 'reviews';
        return `
            <i data-lucide="star" class="w-4 h-4 inline-block fill-amber-400 text-amber-400" aria-hidden="true"></i>
            <span class="font-semibold">${Number(summary.average_rating).toFixed(1)}</span>
            <span class="text-zinc-400 dark:text-zinc-400">(${summary.review_count} ${label})</span>
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
        const dotIndex = text.indexOf('.');
        if (dotIndex !== -1 && dotIndex + 1 <= maxLength) {
            return text.substring(0, dotIndex + 1);
        }
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength).trim() + '...';
    },
};

async function initHomePage() {
    try {
        UIRenderer.init();
        DetailManager.init();
        UIRenderer.showLoading();
        await DataManager.loadData();
        UIRenderer.populateDiplomaFilter();
        BookmarkManager.init();

        const urlParams = new URL(window.location);
        const initialQuery = urlParams.searchParams.get('q') || (typeof INITIAL_QUERY !== 'undefined' ? INITIAL_QUERY : '');
        const initialSchool = urlParams.searchParams.get('school') || 'all';
        const initialDiploma = urlParams.searchParams.get('diploma') || 'all';
        const initialRating = urlParams.searchParams.get('rating') || 'all';
        const initialActive = urlParams.searchParams.get('active') || 'false';
        const initialPage = parseInt(urlParams.searchParams.get('page'), 10) || 1;
        const showBookmarks = urlParams.searchParams.get('bookmarks') === 'true';
        const hasFilters = initialSchool !== 'all' || initialDiploma !== 'all' || initialRating !== 'all' || initialActive === 'true';

        if (initialSchool !== 'all' && UIRenderer.schoolFilter) UIRenderer.schoolFilter.value = initialSchool;
        if (initialDiploma !== 'all' && UIRenderer.diplomaFilter) UIRenderer.diplomaFilter.value = initialDiploma;
        if (initialRating !== 'all' && UIRenderer.ratingFilter) UIRenderer.ratingFilter.value = initialRating;
        if (initialActive === 'true' && UIRenderer.activeFilter && UIRenderer.activeFilter.dataset.active === 'false') {
            UIRenderer.activeFilter.dataset.active = 'true';
            UIRenderer.activeFilter.className = ACTIVE_BTN_CLASSES.active;
            const label = UIRenderer.activeFilter.querySelector('span');
            if (label) label.textContent = 'Active';
        }

        if (showBookmarks) {
            const bookmarkedModules = BookmarkManager.getModules();
            UIRenderer.filteredModules = bookmarkedModules;
            window.currentFilteredModules = bookmarkedModules; // #5
            UIRenderer.currentPage = initialPage;
            UIRenderer.renderPaginatedResults(bookmarkedModules);
            UIRenderer.updateResultsCount(bookmarkedModules.length);
        } else if (initialQuery || hasFilters) {
            if (initialQuery) UIRenderer.searchInput.value = initialQuery;
            UIRenderer.handleSearch(initialQuery, initialPage);
        } else {
            UIRenderer.filteredModules = DataManager.modules;
            window.currentFilteredModules = DataManager.modules; // #5
            UIRenderer.currentPage = initialPage;
            UIRenderer.renderPaginatedResults(DataManager.modules);
            UIRenderer.updateResultsCount(DataManager.modules.length);
        }
    } catch (error) {
        console.error('Failed to initialize app:', error);
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) spinner.classList.add('hidden');
        document.getElementById('resultsContainer').innerHTML = `
            <div class="col-span-full py-16 text-center">
                <div class="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50 dark:bg-red-900/30 mb-4">
                    <i data-lucide="triangle-alert" class="w-8 h-8 text-red-500 dark:text-red-400"></i>
                </div>
                <h3 class="text-xl font-semibold text-zinc-700 dark:text-zinc-200 mb-1">Failed to load module data</h3>
                <p class="text-zinc-500 dark:text-zinc-400">Please refresh the page or try again later.</p>
            </div>
        `;
        lucide.createIcons();
    }
}

document.addEventListener('DOMContentLoaded', () => initHomePage());
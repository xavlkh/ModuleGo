/**
 * Manages the two-module comparison page with infinite scroll.
 * @module comparison
 */
const ComparisonManager = {
    modules: [],
    selected: { one: null, two: null },
    elements: {},
    observers: {},
    comparisonRequestId: 0,
    pagination: {
        one: { page: 1, perPage: 15, loading: false, hasMore: true, query: '' },
        two: { page: 1, perPage: 15, loading: false, hasMore: true, query: '' }
    },

    /**
     * Bootstrap the comparison page: cache elements, load data, bind search inputs.
     */
    async init() {
        this.cacheElements();
        if (!this.elements.searchOne || !this.elements.searchTwo) return;

        try {
            await DataManager.loadData();
        } catch (error) {
            console.error('Failed to load data:', error);
            this.showMessage('Failed to load module data. Please refresh the page.', 'error');
            return;
        }

        this.modules = DataManager.modules.slice().sort((a, b) => (a.code || '').localeCompare(b.code || ''));

        if (this.modules.length === 0) {
            this.showMessage('No module data available. Please refresh the page.', 'error');
            return;
        }

        this.bindSearch('one');
        this.bindSearch('two');
        this.showStarterResults();
        this.restoreFromUrl();
        this.bindShareButton();
    },

    /**
     * Cache frequently accessed DOM elements to avoid repeated queries.
     */
    cacheElements() {
        this.elements = {
            searchOne: document.getElementById('compareSearchOne'),
            searchTwo: document.getElementById('compareSearchTwo'),
            resultsOne: document.getElementById('compareResultsOne'),
            resultsTwo: document.getElementById('compareResultsTwo'),
            selectedOne: document.getElementById('compareSelectedOne'),
            selectedTwo: document.getElementById('compareSelectedTwo'),
            message: document.getElementById('comparisonMessage'),
            tableWrap: document.getElementById('comparisonTableWrap'),
            tableBody: document.getElementById('comparisonTableBody'),
            headerOne: document.getElementById('compareHeaderOne'),
            headerTwo: document.getElementById('compareHeaderTwo')
        };
    },

    /**
     * Bind input and focus event listeners for a search slot.
     * @param {string} slot - 'one' or 'two'
     */
    bindSearch(slot) {
        const input = this.getSlotElement(slot, 'search');
        input.addEventListener('input', () => {
            this.pagination[slot].query = input.value;
            this.renderSearchResults(slot, input.value);
            this.setupObserver(slot);
        });
        input.addEventListener('focus', () => {
            this.pagination[slot].query = input.value;
            this.renderSearchResults(slot, input.value);
            this.setupObserver(slot);
        });
    },

    /**
     * Render initial empty search results for both slots and set up infinite scroll.
     */
    showStarterResults() {
        this.renderSearchResults('one', '');
        this.renderSearchResults('two', '');
        this.setupObserver('one');
        this.setupObserver('two');
    },

    /**
     * Render a page of search results with a sentinel for infinite scroll.
     * @param {string} slot - 'one' or 'two'
     * @param {string} query - search term
     */
    renderSearchResults(slot, query) {
        const resultsElement = this.getSlotElement(slot, 'results');
        const pag = this.pagination[slot];

        pag.page = 1;
        pag.hasMore = true;
        pag.loading = false;

        const matches = this.findMatches(query);
        const batch = matches.slice(0, pag.perPage);
        pag.hasMore = batch.length < matches.length;

        if (matches.length === 0) {
            resultsElement.innerHTML = '<div class="rounded-xl border border-dashed border-zinc-200 dark:border-zinc-700 bg-zinc-50/60 dark:bg-zinc-800/60 px-4 py-3 text-sm text-zinc-400 dark:text-zinc-400">No matching modules found</div>';
            return;
        }

        resultsElement.innerHTML = this.buildButtonsHtml(batch, slot) + this.buildSentinelHtml(pag.hasMore, slot);

        this.bindResultButtons(resultsElement, slot);
    },

    /**
     * @param {Array} modules - modules to render
     * @param {string} slot - 'one' or 'two'
     * @returns {string}
     */
    buildButtonsHtml(modules, slot) {
        return modules.map(m => `
            <button class="w-full text-left rounded-xl bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 shadow-sm px-4 py-3 transition-all hover:border-primary-300 dark:hover:border-primary-500 hover:shadow-md" type="button" data-slot="${slot}" data-code="${escapeHtml(m.code)}">
                <div class="text-xs font-bold text-primary-600 dark:text-primary-400 mb-0.5">${escapeHtml(m.code)}</div>
                <div class="text-sm font-semibold text-zinc-900 dark:text-white leading-snug">${escapeHtml(m.name)}</div>
                <div class="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">${escapeHtml(m.school || 'School not listed')}</div>
            </button>
        `).join('');
    },

    /**
     * @param {boolean} show - whether to show the sentinel
     * @returns {string}
     */
    buildSentinelHtml(show, slot) {
        if (!show) return '';
        return `<div id="scrollSentinel-${slot}" class="flex justify-center py-3"><div class="h-5 w-5 animate-spin rounded-full border-2 border-zinc-300 border-t-primary-500"></div></div>`;
    },

    /**
     * @param {HTMLElement} container
     * @param {string} slot
     */
    bindResultButtons(container, slot) {
        container.querySelectorAll('button[data-code]').forEach(btn => {
            btn.addEventListener('click', () => this.selectModule(btn.dataset.slot, btn.dataset.code));
        });
    },

    /**
     * Append the next batch of results for infinite scroll.
     * @param {string} slot - 'one' or 'two'
     */
    loadMore(slot) {
        const pag = this.pagination[slot];
        if (pag.loading || !pag.hasMore) return;

        pag.loading = true;
        pag.page++;

        const matches = this.findMatches(pag.query);
        const start = (pag.page - 1) * pag.perPage;
        const batch = matches.slice(start, start + pag.perPage);
        pag.hasMore = (start + batch.length) < matches.length;

        const resultsElement = this.getSlotElement(slot, 'results');
        const sentinel = document.getElementById(`scrollSentinel-${slot}`);

        const fragment = document.createRange().createContextualFragment(this.buildButtonsHtml(batch, slot));

        if (sentinel) {
            sentinel.remove();
        }
        resultsElement.appendChild(fragment);
        if (pag.hasMore) {
            resultsElement.insertAdjacentHTML('beforeend', this.buildSentinelHtml(true, slot));
        }

        this.bindResultButtons(resultsElement, slot);
        this.setupObserver(slot);
        pag.loading = false;
    },

    /**
     * Set up or reset an IntersectionObserver for a slot's sentinel.
     * @param {string} slot - 'one' or 'two'
     */
    setupObserver(slot) {
        if (this.observers[slot]) {
            this.observers[slot].disconnect();
        }

        const resultsElement = this.getSlotElement(slot, 'results');

        this.observers[slot] = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadMore(slot);
                }
            });
        }, { root: resultsElement, threshold: 0 });

        const sentinel = document.getElementById(`scrollSentinel-${slot}`);
        if (sentinel) {
            this.observers[slot].observe(sentinel);
        }
    },

    /**
     * @param {string} query - search term
     * @returns {Array}
     */
    findMatches(query) {
        const term = query.trim().toLowerCase();
        if (!term) return this.modules;
        return this.modules.filter(m => {
            const code = (m.code || '').toLowerCase();
            const name = (m.name || '').toLowerCase();
            return code.includes(term) || name.includes(term);
        });
    },

    restoreFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const codes = params.getAll('id').map(c => c.trim().toUpperCase()).filter(Boolean);
        if (codes.length >= 1 && DataManager.getModule(codes[0])) {
            this.selectModule('one', codes[0], true);
        }
        if (codes.length >= 2 && DataManager.getModule(codes[1])) {
            this.selectModule('two', codes[1], true);
        }
    },

    updateUrl() {
        const codes = [];
        if (this.selected.one) codes.push(this.selected.one.code);
        if (this.selected.two) codes.push(this.selected.two.code);
        const url = new URL(window.location);
        url.searchParams.delete('id');
        codes.forEach(c => url.searchParams.append('id', c));
        if (codes.length === 0) url.search = '';
        window.history.replaceState({}, '', url);
    },

    bindShareButton() {
        const btn = document.getElementById('shareComparison');
        if (!btn) return;
        btn.addEventListener('click', () => ShareManager.copyLink(btn));
    },

    selectModule(slot, code, silent = false) {
        const module = DataManager.getModule(code);
        if (!module) return;
        this.selected[slot] = module;

        const input = this.getSlotElement(slot, 'search');
        const selectedEl = this.getSlotElement(slot, 'selected');
        const resultsEl = this.getSlotElement(slot, 'results');

        input.value = '';
        selectedEl.classList.remove('hidden');
        selectedEl.innerHTML = `
            <span class="flex-1">
                <strong class="text-primary-700 dark:text-primary-400 mr-1">${escapeHtml(module.code)}</strong>
                <span class="text-zinc-900 dark:text-white">${escapeHtml(module.name)}</span>
            </span>
            <button type="button" class="flex h-7 w-7 items-center justify-center rounded-lg module-code-box text-primary-600 dark:text-primary-300 hover:bg-primary-500 hover:text-white transition-all" aria-label="Clear selected module" data-slot="${slot}">
                <i data-lucide="x" class="w-3.5 h-3.5"></i>
            </button>
        `;
        resultsEl.innerHTML = '';
        selectedEl.querySelector('button').addEventListener('click', () => this.clearSelection(slot));
        lucide.createIcons();
        if (!silent) this.updateUrl();
        this.renderComparison();
    },

    /**
     * Clear the selected module for a slot and restore search results.
     * @param {string} slot - 'one' or 'two'
     */
    clearSelection(slot) {
        this.selected[slot] = null;
        this.getSlotElement(slot, 'selected').classList.add('hidden');
        this.renderSearchResults(slot, '');
        this.setupObserver(slot);
        this.updateUrl();
        this.renderComparison();
    },

    /**
     * Render the comparison table for the two selected modules.
     * Shows a message if fewer than two distinct modules are selected.
     */
    renderComparison() {
        const first = this.selected.one;
        const second = this.selected.two;

        // Increment request ID to cancel any in-flight Gemini API calls
        if (!first || !second) {
            this.comparisonRequestId++;
            this.showMessage('Select two different modules to start comparing.');
            return;
        }
        if (first.code === second.code) {
            this.comparisonRequestId++;
            this.showMessage('Choose two different modules for a useful comparison.');
            return;
        }

        this.elements.message.classList.add('hidden');
        this.elements.tableWrap.classList.remove('hidden');
        this.elements.headerOne.textContent = `${first.code} - ${first.name}`;
        this.elements.headerTwo.textContent = `${second.code} - ${second.name}`;
        this.renderComparisonRows(first, second, null, true);
        this.loadDynamicComparison(first, second);
    },

    /**
     * Render stable catalogue/rating rows and transient Gemini result rows.
     * @param {Object} first - First selected module.
     * @param {Object} second - Second selected module.
     * @param {Array<Object>|null} generatedModules - Gemini module results.
     * @param {boolean} loading - Whether Gemini is still generating.
     * @param {string} errorMessage - Safe user-facing generation error.
     */
    renderComparisonRows(first, second, generatedModules, loading = false, errorMessage = '') {
        const placeholder = '<span class="text-zinc-400 dark:text-zinc-400">Not available</span>';
        const generatedByCode = new Map(
            (generatedModules || []).map(module => [
                String(module.module_code || '').toUpperCase(),
                module
            ])
        );
        const firstGenerated = generatedByCode.get(first.code);
        const secondGenerated = generatedByCode.get(second.code);
        const dynamicPlaceholder = loading
            ? '<span class="inline-flex items-center gap-2 text-zinc-500 dark:text-zinc-400" role="status"><span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-zinc-300 border-t-primary-500"></span>Generating with Gemini...</span>'
            : `<span class="text-amber-700 dark:text-amber-300">${escapeHtml(errorMessage || 'AI comparison unavailable.')}</span>`;
        const rows = [
            ['Module code', escapeHtml(first.code), escapeHtml(second.code)],
            ['Module name', escapeHtml(first.name), escapeHtml(second.name)],
            ['School', first.school ? escapeHtml(first.school) : placeholder, second.school ? escapeHtml(second.school) : placeholder],
            ['Student rating', this.formatRating(first.code), this.formatRating(second.code)],
            ['AI summary', firstGenerated ? escapeHtml(firstGenerated.summary) : dynamicPlaceholder, secondGenerated ? escapeHtml(secondGenerated.summary) : dynamicPlaceholder],
            ['Suitable for', firstGenerated ? escapeHtml(firstGenerated.suitable_for) : dynamicPlaceholder, secondGenerated ? escapeHtml(secondGenerated.suitable_for) : dynamicPlaceholder],
            ['Estimated workload', firstGenerated ? this.formatWorkload(firstGenerated.workload) : dynamicPlaceholder, secondGenerated ? this.formatWorkload(secondGenerated.workload) : dynamicPlaceholder]
        ];

        this.elements.tableBody.innerHTML = rows.map(([label, v1, v2], i) => `
            <tr class="bg-primary-50/40 dark:bg-primary-900/20">
                <th scope="row" class="px-5 py-3.5 text-sm font-semibold text-primary-800 dark:text-primary-200">${escapeHtml(label)}</th>
                <td class="px-5 py-3.5 text-sm text-zinc-700 dark:text-zinc-300 whitespace-normal break-words overflow-hidden">${v1}</td>
                <td class="px-5 py-3.5 text-sm text-zinc-700 dark:text-zinc-300 whitespace-normal break-words overflow-hidden">${v2}</td>
            </tr>
        `).join('');
        lucide.createIcons();
    },

    /**
     * Request a fresh Gemini comparison after two different modules are selected.
     * Results are intentionally not persisted by the browser or backend.
     * @param {Object} first - First selected module.
     * @param {Object} second - Second selected module.
     */
    async loadDynamicComparison(first, second) {
        const requestId = ++this.comparisonRequestId;
        try {
            const response = await fetch('/api/comparison/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    module_codes: [first.code, second.code]
                })
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload.error || 'Dynamic comparison is unavailable.');
            }
            if (requestId !== this.comparisonRequestId) return;
            this.renderComparisonRows(first, second, payload.modules);
        } catch (error) {
            if (requestId !== this.comparisonRequestId) return;
            console.error('Error generating module comparison:', error);
            this.renderComparisonRows(
                first,
                second,
                null,
                false,
                error.message || 'Dynamic comparison is unavailable.'
            );
        }
    },

    /**
     * Format a stored student rating for a comparison-table cell.
     * @param {string} moduleCode - Module code used by the ratings API.
     * @returns {string} Safe HTML for the rating cell.
     */
    formatRating(moduleCode) {
        const rating = DataManager.getRatingSummary(moduleCode);
        if (!rating.review_count || rating.average_rating === null) {
            return '<span class="text-zinc-400 dark:text-zinc-400">No ratings yet</span>';
        }
        const reviewLabel = rating.review_count === 1 ? 'review' : 'reviews';
        return `
            <span class="inline-flex flex-wrap items-center gap-1.5">
                <span class="inline-flex items-center gap-1 font-semibold text-amber-600 dark:text-amber-400">
                    <i data-lucide="star" class="h-4 w-4 fill-current" aria-hidden="true"></i>
                    ${Number(rating.average_rating).toFixed(1)} / 5
                </span>
                <span class="text-zinc-500 dark:text-zinc-400">(${rating.review_count} ${reviewLabel})</span>
            </span>
        `;
    },

    /**
     * Format Gemini's workload estimate with its confidence and reason.
     * @param {Object} workload - Structured workload estimate.
     * @returns {string} Safe HTML for the workload cell.
     */
    formatWorkload(workload) {
        if (!workload) {
            return '<span class="text-zinc-400 dark:text-zinc-400">Unknown</span>';
        }
        return `
            <div>
                <strong>${escapeHtml(workload.level || 'Unknown')}</strong>
                <span class="text-xs text-zinc-500 dark:text-zinc-400"> · ${escapeHtml(workload.confidence || 'Low')} confidence</span>
                <p class="text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">${escapeHtml(workload.reason || 'Insufficient synopsis evidence.')}</p>
            </div>
        `;
    },

    /**
     * Display a message and hide the comparison table.
     * @param {string} text - The message text.
     */
    showMessage(text, type = 'warning') {
        const colors = {
            info: 'border-primary-200 dark:border-primary-700 bg-primary-50 dark:bg-primary-900/30 text-primary-800 dark:text-primary-200',
            warning: 'border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200',
            error: 'border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/30 text-red-800 dark:text-red-200',
        };
        this.elements.message.innerHTML = `<div class="rounded-xl border px-5 py-4 text-sm ${colors[type] || colors.warning}" role="alert">${escapeHtml(text)}</div>`;
        this.elements.message.classList.remove('hidden');
        this.elements.tableWrap.classList.add('hidden');
    },

    /**
     * Get a cached DOM element by slot and type.
     * @param {string} slot - 'one' or 'two'
     * @param {string} type - Element type prefix (e.g. 'search', 'results', 'selected')
     * @returns {HTMLElement} The matching DOM element.
     */
    getSlotElement(slot, type) {
        return this.elements[`${type}${slot.charAt(0).toUpperCase()}${slot.slice(1)}`];
    }
};

document.addEventListener('DOMContentLoaded', () => ComparisonManager.init());

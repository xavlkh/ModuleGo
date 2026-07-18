/**
 * Manages the two-module comparison page with infinite scroll.
 * @module comparison
 */
const ComparisonManager = {
    modules: [],
    selected: { one: null, two: null },
    elements: {},
    observers: {},
    pagination: {
        one: { page: 1, perPage: 15, loading: false, hasMore: true, query: '' },
        two: { page: 1, perPage: 15, loading: false, hasMore: true, query: '' }
    },

    async init() {
        this.cacheElements();
        if (!this.elements.searchOne || !this.elements.searchTwo) return;

        await DataManager.loadData();
        this.modules = DataManager.modules.slice().sort((a, b) => (a.code || '').localeCompare(b.code || ''));
        this.bindSearch('one');
        this.bindSearch('two');
        this.showStarterResults();
    },

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
            resultsElement.innerHTML = '<div class="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/60 px-4 py-3 text-sm text-slate-400 dark:text-slate-400">No matching modules found</div>';
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
            <button class="w-full text-left rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm px-4 py-3 transition-all hover:border-primary-300 dark:hover:border-primary-500 hover:shadow-md" type="button" data-slot="${slot}" data-code="${escapeHtml(m.code)}">
                <div class="text-xs font-bold text-primary-600 dark:text-primary-400 mb-0.5">${escapeHtml(m.code)}</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white leading-snug">${escapeHtml(m.name)}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">${escapeHtml(m.school || 'School not listed')}</div>
            </button>
        `).join('');
    },

    /**
     * @param {boolean} show - whether to show the sentinel
     * @returns {string}
     */
    buildSentinelHtml(show, slot) {
        if (!show) return '';
        return `<div id="scrollSentinel-${slot}" class="flex justify-center py-3"><div class="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-primary-500"></div></div>`;
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

    selectModule(slot, code) {
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
                <span class="text-slate-900 dark:text-white">${escapeHtml(module.name)}</span>
            </span>
            <button type="button" class="flex h-7 w-7 items-center justify-center rounded-lg module-code-box text-primary-600 dark:text-primary-300 hover:bg-primary-500 hover:text-white transition-all" aria-label="Clear selected module" data-slot="${slot}">
                <i data-lucide="x" class="w-3.5 h-3.5"></i>
            </button>
        `;
        resultsEl.innerHTML = '';
        selectedEl.querySelector('button').addEventListener('click', () => this.clearSelection(slot));
        lucide.createIcons();
        this.renderComparison();
    },

    clearSelection(slot) {
        this.selected[slot] = null;
        this.getSlotElement(slot, 'selected').classList.add('hidden');
        this.renderSearchResults(slot, '');
        this.setupObserver(slot);
        this.renderComparison();
    },

    renderComparison() {
        const first = this.selected.one;
        const second = this.selected.two;

        if (!first || !second) {
            this.showMessage('Select two different modules to start comparing.');
            return;
        }
        if (first.code === second.code) {
            this.showMessage('Choose two different modules for a useful comparison.');
            return;
        }

        this.elements.message.classList.add('hidden');
        this.elements.tableWrap.classList.remove('hidden');
        this.elements.headerOne.textContent = `${first.code} - ${first.name}`;
        this.elements.headerTwo.textContent = `${second.code} - ${second.name}`;

        const placeholder = '<span class="text-slate-400 dark:text-slate-400">Not available</span>';
        const rows = [
            ['Module code', escapeHtml(first.code), escapeHtml(second.code)],
            ['Module name', escapeHtml(first.name), escapeHtml(second.name)],
            ['School', escapeHtml(first.school), escapeHtml(second.school)],
            ['Summary', first.summary ? escapeHtml(first.summary) : placeholder, second.summary ? escapeHtml(second.summary) : placeholder],
            ['Suitable for', first.suitableFor ? escapeHtml(first.suitableFor) : placeholder, second.suitableFor ? escapeHtml(second.suitableFor) : placeholder]
        ];

        this.elements.tableBody.innerHTML = rows.map(([label, v1, v2], i) => `
            <tr class="${i < 2 ? 'bg-primary-50/40 dark:bg-primary-900/20' : ''}">
                <th scope="row" class="px-5 py-3.5 text-sm font-semibold text-primary-800 dark:text-primary-200 whitespace-nowrap">${escapeHtml(label)}</th>
                <td class="px-5 py-3.5 text-sm text-slate-700 dark:text-slate-300">${v1}</td>
                <td class="px-5 py-3.5 text-sm text-slate-700 dark:text-slate-300">${v2}</td>
            </tr>
        `).join('');
        lucide.createIcons();
    },

    showMessage(text) {
        this.elements.message.textContent = text;
        this.elements.message.classList.remove('hidden');
        this.elements.tableWrap.classList.add('hidden');
    },

    getSlotElement(slot, type) {
        return this.elements[`${type}${slot.charAt(0).toUpperCase()}${slot.slice(1)}`];
    }
};

document.addEventListener('DOMContentLoaded', () => ComparisonManager.init());

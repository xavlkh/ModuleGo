// Manages the two-module comparison page.
const ComparisonManager = {
    modules: [],
    selected: {
        one: null,
        two: null
    },
    elements: {},

    async init() {
        // Stop if this script is not on the comparison page.
        this.cacheElements();
        if (!this.elements.searchOne || !this.elements.searchTwo) return;

        // Load and sort modules for both search boxes.
        await DataManager.loadData();
        this.modules = DataManager.modules.slice().sort((a, b) => (a.code || '').localeCompare(b.code || ''));
        this.bindSearch('one');
        this.bindSearch('two');
        this.showStarterResults();
    },

    cacheElements() {
        // Store page elements used by the comparison UI.
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
        // Connect one search box to its result list.
        const input = this.getSlotElement(slot, 'search');

        input.addEventListener('input', () => {
            this.renderSearchResults(slot, input.value);
        });

        input.addEventListener('focus', () => {
            this.renderSearchResults(slot, input.value);
        });
    },

    showStarterResults() {
        // Show a few options before the user types.
        this.renderSearchResults('one', '');
        this.renderSearchResults('two', '');
    },

    renderSearchResults(slot, query) {
        // Render matching modules for one side.
        const resultsElement = this.getSlotElement(slot, 'results');
        const matches = this.findMatches(query);

        if (matches.length === 0) {
            resultsElement.innerHTML = '<div class="comparison-empty-result">No matching modules found</div>';
            return;
        }

        resultsElement.innerHTML = matches.map(module => `
            <button class="comparison-result" type="button" data-slot="${slot}" data-code="${this.escapeHtml(module.code)}">
                <span class="comparison-result-code">${this.escapeHtml(module.code)}</span>
                <span class="comparison-result-name">${this.escapeHtml(module.name)}</span>
                <span class="comparison-result-school">${this.escapeHtml(module.school || 'School not listed')}</span>
            </button>
        `).join('');

        resultsElement.querySelectorAll('.comparison-result').forEach(button => {
            button.addEventListener('click', () => {
                this.selectModule(button.dataset.slot, button.dataset.code);
            });
        });
    },

    findMatches(query) {
        // Keep suggestions short and easy to scan.
        const searchTerm = query.trim().toLowerCase();
        const source = searchTerm
            ? this.modules.filter(module => {
                const code = (module.code || '').toLowerCase();
                const name = (module.name || '').toLowerCase();
                return code.includes(searchTerm) || name.includes(searchTerm);
            })
            : this.modules;

        return source.slice(0, 6);
    },

    selectModule(slot, code) {
        // Save the selected module for one side.
        const module = DataManager.getModule(code);
        if (!module) return;

        this.selected[slot] = module;

        const input = this.getSlotElement(slot, 'search');
        const selectedElement = this.getSlotElement(slot, 'selected');
        const resultsElement = this.getSlotElement(slot, 'results');

        input.value = '';
        selectedElement.classList.remove('d-none');
        selectedElement.innerHTML = `
            <span>
                <strong>${this.escapeHtml(module.code)}</strong>
                ${this.escapeHtml(module.name)}
            </span>
            <button type="button" aria-label="Clear selected module" data-slot="${slot}">
                <i class="bi bi-x-lg"></i>
            </button>
        `;
        resultsElement.innerHTML = '';

        selectedElement.querySelector('button').addEventListener('click', () => {
            this.clearSelection(slot);
        });

        this.renderComparison();
    },

    clearSelection(slot) {
        // Remove one selected module.
        this.selected[slot] = null;
        this.getSlotElement(slot, 'selected').classList.add('d-none');
        this.renderSearchResults(slot, '');
        this.renderComparison();
    },

    renderComparison() {
        // Build the comparison table when both modules are chosen.
        const firstModule = this.selected.one;
        const secondModule = this.selected.two;

        if (!firstModule || !secondModule) {
            this.showMessage('Select two different modules to start comparing.');
            return;
        }

        if (firstModule.code === secondModule.code) {
            this.showMessage('Choose two different modules for a useful comparison.');
            return;
        }

        this.elements.message.classList.add('d-none');
        this.elements.tableWrap.classList.remove('d-none');
        this.elements.headerOne.textContent = `${firstModule.code} - ${firstModule.name}`;
        this.elements.headerTwo.textContent = `${secondModule.code} - ${secondModule.name}`;

        const rows = [
            ['Module code', firstModule.code, secondModule.code],
            ['Module name', firstModule.name, secondModule.name],
            ['School', firstModule.school, secondModule.school],
            ['Features', this.getPendingField(firstModule, 'features'), this.getPendingField(secondModule, 'features')],
            ['Suitable for', this.getPendingField(firstModule, 'suitableFor'), this.getPendingField(secondModule, 'suitableFor')]
        ];

        this.elements.tableBody.innerHTML = rows.map(([label, firstValue, secondValue]) => `
            <tr>
                <th scope="row">${this.escapeHtml(label)}</th>
                <td>${this.formatValue(firstValue)}</td>
                <td>${this.formatValue(secondValue)}</td>
            </tr>
        `).join('');
    },

    showMessage(text) {
        // Show guidance instead of the table.
        this.elements.message.textContent = text;
        this.elements.message.classList.remove('d-none');
        this.elements.tableWrap.classList.add('d-none');
    },

    getSlotElement(slot, type) {
        // Convert slot names into cached element keys.
        const key = `${type}${slot.charAt(0).toUpperCase()}${slot.slice(1)}`;
        return this.elements[key];
    },

    getPendingField(module, fieldName) {
        // Some generated comparison fields may be missing.
        return module[fieldName] || '<span class="text-muted">Not added yet</span>';
    },

    formatValue(value) {
        // Escape normal text but allow known muted placeholders.
        if (!value) return '<span class="text-muted">Not available</span>';
        if (String(value).includes('<span')) return value;
        return this.escapeHtml(value);
    },

    escapeHtml(value) {
        // Prevent module text from becoming HTML.
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    ComparisonManager.init();
});

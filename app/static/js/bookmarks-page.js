/**
 * Render and manage the dedicated bookmarked modules page.
 * @module bookmarks-page
 */
const BookmarksPage = {
    /** Initialise the page and load catalogue data. */
    async init() {
        this.grid = document.getElementById('bookmarkGrid');
        this.loading = document.getElementById('bookmarkLoading');
        this.empty = document.getElementById('bookmarkEmpty');
        this.error = document.getElementById('bookmarkError');
        this.count = document.getElementById('bookmarkCount');
        this.clearButton = document.getElementById('clearBookmarksBtn');

        this.clearButton.addEventListener('click', () => this.clearAll());
        document.addEventListener('bookmarks:changed', () => this.render());
        document.addEventListener('ratings:changed', () => this.render());

        try {
            await DataManager.loadData();
            BookmarkManager.init();
            DetailManager.init();
            this.render();
        } catch (error) {
            console.error('Failed to initialise bookmarks page:', error);
            this.loading.classList.add('hidden');
            this.error.classList.remove('hidden');
            this.count.textContent = 'Unavailable';
        }
    },

    /** Render the current bookmark collection. */
    render() {
        const modules = BookmarkManager.getModules();
        this.loading.classList.add('hidden');
        this.error.classList.add('hidden');
        this.count.textContent = `${modules.length} module${modules.length === 1 ? '' : 's'}`;
        this.clearButton.classList.toggle('hidden', modules.length === 0);
        this.empty.classList.toggle('hidden', modules.length !== 0);
        this.grid.classList.toggle('hidden', modules.length === 0);
        this.grid.innerHTML = '';

        modules.forEach(module => this.grid.appendChild(this.createModuleCard(module)));
        lucide.createIcons();
    },

    /**
     * Create a bookmarked module card.
     * @param {Object} module - Module catalogue record.
     * @returns {HTMLDivElement} Card wrapper.
     */
    createModuleCard(module) {
        const wrapper = document.createElement('div');
        const synopsis = String(module.synopsis || 'No synopsis available.');
        const description = synopsis.length > 150
            ? `${synopsis.substring(0, 150).trim()}...`
            : synopsis;
        const rating = DataManager.getRatingSummary(module.code);
        const ratingMarkup = rating.review_count
            ? `<i data-lucide="star" class="inline-block h-4 w-4 fill-amber-400 text-amber-400" aria-hidden="true"></i><span class="font-semibold">${Number(rating.average_rating).toFixed(1)}</span><span class="text-zinc-400 dark:text-zinc-400">(${rating.review_count})</span>`
            : '<i data-lucide="star" class="inline-block h-4 w-4" aria-hidden="true"></i><span class="text-zinc-400 dark:text-zinc-400">No reviews yet</span>';

        wrapper.className = 'col-span-1';
        wrapper.innerHTML = `
            <article class="glass-card group flex h-full cursor-pointer flex-col p-5" data-code="${escapeHtml(module.code)}">
                <div class="mb-1.5 text-xs font-bold uppercase tracking-wider text-primary-500 dark:text-primary-400">${escapeHtml(module.code)}</div>
                <h3 class="mb-2 text-base font-bold leading-snug text-zinc-900 transition-colors group-hover:text-primary-600 dark:text-white dark:group-hover:text-primary-400">${escapeHtml(module.name)}</h3>
                <p class="mb-3 line-clamp-3 flex-1 text-sm text-zinc-500 dark:text-zinc-400">${escapeHtml(description)}</p>
                <div class="mb-3"><span class="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">${escapeHtml(module.school || 'School not listed')}</span></div>
                <div class="mb-3 flex items-center gap-1 text-sm text-amber-600 dark:text-amber-400">${ratingMarkup}</div>
                <div class="flex items-center justify-between gap-2 border-t border-zinc-100 pt-3 dark:border-zinc-700/50">
                    <button type="button" class="btn-outline px-3 py-1.5 text-xs"><i data-lucide="info" class="mr-1 inline-block h-3.5 w-3.5"></i>View Details</button>
                    <button type="button" class="remove-bookmark-btn inline-flex items-center px-2 py-1 text-xs font-medium text-zinc-400 transition-colors hover:text-red-600 dark:text-zinc-400 dark:hover:text-red-400" aria-label="Remove ${escapeHtml(module.code)} from bookmarks"><i data-lucide="bookmark-x" class="mr-1 inline-block h-3.5 w-3.5"></i>Remove</button>
                </div>
            </article>`;

        wrapper.querySelector('article').addEventListener('click', () => {
            DetailManager.showModuleDetail(module.code);
        });
        wrapper.querySelector('.remove-bookmark-btn').addEventListener('click', event => {
            event.stopPropagation();
            BookmarkManager.remove(module.code);
        });
        return wrapper;
    },

    /** Remove every bookmark after user confirmation. */
    clearAll() {
        if (window.confirm('Remove all bookmarked modules?')) {
            BookmarkManager.clear();
        }
    },
};

document.addEventListener('DOMContentLoaded', () => BookmarksPage.init());

/**
 * Manage bookmarked modules using localStorage.
 * @module bookmark
 */
const BookmarkManager = {
    storageKey: 'moduleGoBookmarks',

    /**
     * Store bookmarked module codes.
     * @type {Array<string>}
     */
    bookmarks: [],

    /**
     * Initialise bookmark data.
     */
    init() {
        this.load();
    },

    /** Notify active pages that the bookmark collection changed. */
    notifyChanged() {
        document.dispatchEvent(new CustomEvent('bookmarks:changed', {
            detail: { codes: this.getCodes() },
        }));
    },

    /**
     * Load bookmarked module codes from localStorage.
     */
    load() {
        try {
            const savedBookmarks =
                localStorage.getItem(this.storageKey);

            const parsedBookmarks =
                savedBookmarks
                    ? JSON.parse(savedBookmarks)
                    : [];

            if (!Array.isArray(parsedBookmarks)) {
                this.bookmarks = [];
                return;
            }

            this.bookmarks = [
                ...new Set(
                    parsedBookmarks
                        .map(code =>
                            String(code || '')
                                .trim()
                                .toUpperCase()
                        )
                        .filter(Boolean)
                ),
            ];
        } catch (error) {
            console.error(
                'Failed to load bookmarks:',
                error
            );

            this.bookmarks = [];
        }
    },

    /**
     * Save bookmarked module codes to localStorage.
     */
    save() {
        try {
            localStorage.setItem(
                this.storageKey,
                JSON.stringify(this.bookmarks)
            );
        } catch (error) {
            console.error(
                'Failed to save bookmarks:',
                error
            );
        }
    },

    /**
     * Check whether a module is bookmarked.
     *
     * @param {string} moduleCode
     * @returns {boolean}
     */
    isBookmarked(moduleCode) {
        const code =
            String(moduleCode || '')
                .trim()
                .toUpperCase();

        if (!code) {
            return false;
        }

        return this.bookmarks.includes(code);
    },

    /**
     * Add or remove a module bookmark.
     *
     * @param {string} moduleCode
     * @returns {boolean} Current bookmark status
     */
    toggle(moduleCode) {
        const code =
            String(moduleCode || '')
                .trim()
                .toUpperCase();

        if (!code) {
            return false;
        }

        if (this.bookmarks.includes(code)) {
            this.bookmarks =
                this.bookmarks.filter(
                    savedCode =>
                        savedCode !== code
                );
        } else {
            this.bookmarks.push(code);
        }

        this.save();
        this.notifyChanged();

        return this.bookmarks.includes(code);
    },

    /**
     * Add a bookmark.
     *
     * @param {string} moduleCode
     * @returns {boolean}
     */
    add(moduleCode) {
        const code =
            String(moduleCode || '')
                .trim()
                .toUpperCase();

        if (!code) {
            return false;
        }

        if (!this.bookmarks.includes(code)) {
            this.bookmarks.push(code);
            this.save();
            this.notifyChanged();
        }

        return true;
    },

    /**
     * Remove a bookmark.
     *
     * @param {string} moduleCode
     * @returns {boolean}
     */
    remove(moduleCode) {
        const code =
            String(moduleCode || '')
                .trim()
                .toUpperCase();

        if (!code) {
            return false;
        }

        const originalLength =
            this.bookmarks.length;

        this.bookmarks =
            this.bookmarks.filter(
                savedCode =>
                    savedCode !== code
            );

        if (
            this.bookmarks.length !==
            originalLength
        ) {
            this.save();
            this.notifyChanged();
            return true;
        }

        return false;
    },

    /**
     * Return bookmarked module codes.
     *
     * @returns {Array<string>}
     */
    getCodes() {
        return [...this.bookmarks];
    },

    /**
     * Return bookmarked module objects.
     *
     * @returns {Array<Object>}
     */
    getModules() {
        if (
            typeof DataManager ===
                'undefined' ||
            !Array.isArray(
                DataManager.modules
            )
        ) {
            return [];
        }

        return this.bookmarks
            .map(code =>
                DataManager.getModule(code)
            )
            .filter(Boolean);
    },

    /**
     * Return the number of bookmarks.
     *
     * @returns {number}
     */
    getCount() {
        return this.bookmarks.length;
    },

    /**
     * Remove all bookmarks.
     */
    clear() {
        if (this.bookmarks.length === 0) return;
        this.bookmarks = [];
        this.save();
        this.notifyChanged();
    },
};

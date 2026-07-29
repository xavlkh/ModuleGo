/**
 * Manage bookmarked modules using localStorage.
 * @module bookmark
 */
function _normalizeCode(code) {
    return String(code || '').trim().toUpperCase();
}

const BookmarkManager = {
    storageKey: 'moduleGoBookmarks',
    bookmarks: [],

    init() {
        this.load();
    },

    load() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            const parsed = saved ? JSON.parse(saved) : [];
            if (!Array.isArray(parsed)) {
                this.bookmarks = [];
                return;
            }
            this.bookmarks = [...new Set(parsed.map(_normalizeCode).filter(Boolean))];
        } catch {
            this.bookmarks = [];
        }
    },

    save() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.bookmarks));
        } catch {}
    },

    isBookmarked(moduleCode) {
        const code = _normalizeCode(moduleCode);
        return !!code && this.bookmarks.includes(code);
    },

    toggle(moduleCode) {
        const code = _normalizeCode(moduleCode);
        if (!code) return false;
        if (this.bookmarks.includes(code)) {
            this.bookmarks = this.bookmarks.filter(c => c !== code);
        } else {
            this.bookmarks.push(code);
        }
        this.save();
        return this.bookmarks.includes(code);
    },

    add(moduleCode) {
        const code = _normalizeCode(moduleCode);
        if (!code) return false;
        if (!this.bookmarks.includes(code)) {
            this.bookmarks.push(code);
            this.save();
        }
        return true;
    },

    remove(moduleCode) {
        const code = _normalizeCode(moduleCode);
        if (!code) return false;
        const len = this.bookmarks.length;
        this.bookmarks = this.bookmarks.filter(c => c !== code);
        if (this.bookmarks.length !== len) {
            this.save();
            return true;
        }
        return false;
    },

    getCodes() {
        return [...this.bookmarks];
    },

    getModules() {
        if (typeof DataManager === 'undefined' || !Array.isArray(DataManager.modules)) {
            return [];
        }
        return this.bookmarks.map(code => DataManager.getModule(code)).filter(Boolean);
    },

    getCount() {
        return this.bookmarks.length;
    },

    clear() {
        this.bookmarks = [];
        this.save();
    },
};
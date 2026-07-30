/**
 * Manage guest bookmarks locally and account bookmarks through Flask.
 * @module bookmark
 */
function _normalizeCode(code) {
    return String(code || '').trim().toUpperCase();
}

const BookmarkManager = {
    storageKey: 'moduleGoBookmarks',
    bookmarks: [],
    initialized: false,
    accountMode: Boolean(window.ModuleGoAuth?.authenticated),

    /** Load the correct bookmark store for the current identity. */
    async init() {
        if (this.initialized) return;
        if (this.accountMode) {
            const response = await fetch('/api/bookmarks');
            if (!response.ok) throw new Error('Could not load account bookmarks.');
            const data = await response.json();
            this.bookmarks = [...new Set(
                (data.module_codes || []).map(_normalizeCode).filter(Boolean)
            )];
        } else {
            this.loadLocal();
        }
        this.initialized = true;
    },

    /** Read browser-only guest bookmarks. */
    loadLocal() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            const parsed = saved ? JSON.parse(saved) : [];
            this.bookmarks = Array.isArray(parsed)
                ? [...new Set(parsed.map(_normalizeCode).filter(Boolean))]
                : [];
        } catch {
            this.bookmarks = [];
        }
    },

    /** Save browser-only guest bookmarks. */
    saveLocal() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.bookmarks));
        } catch {}
    },

    /** Notify all pages that bookmark state changed. */
    notify() {
        document.dispatchEvent(new CustomEvent('bookmarks:changed'));
    },

    isBookmarked(moduleCode) {
        const code = _normalizeCode(moduleCode);
        return Boolean(code && this.bookmarks.includes(code));
    },

    /** Toggle a bookmark and return its new state. */
    async toggle(moduleCode) {
        const code = _normalizeCode(moduleCode);
        if (!code) return false;
        if (this.bookmarks.includes(code)) {
            await this.remove(code);
            return false;
        }
        await this.add(code);
        return true;
    },

    /** Add a guest or account bookmark. */
    async add(moduleCode) {
        const code = _normalizeCode(moduleCode);
        if (!code) return false;
        if (this.accountMode) {
            const response = await apiFetch(`/api/bookmarks/${encodeURIComponent(code)}`, {
                method: 'PUT',
            });
            if (!response.ok) throw new Error('Could not add bookmark.');
        }
        if (!this.bookmarks.includes(code)) this.bookmarks.push(code);
        if (!this.accountMode) this.saveLocal();
        this.notify();
        return true;
    },

    /** Remove a guest or account bookmark. */
    async remove(moduleCode) {
        const code = _normalizeCode(moduleCode);
        if (!code) return false;
        if (this.accountMode) {
            const response = await apiFetch(`/api/bookmarks/${encodeURIComponent(code)}`, {
                method: 'DELETE',
            });
            if (!response.ok) throw new Error('Could not remove bookmark.');
        }
        const previousLength = this.bookmarks.length;
        this.bookmarks = this.bookmarks.filter(item => item !== code);
        if (!this.accountMode) this.saveLocal();
        if (previousLength !== this.bookmarks.length) this.notify();
        return previousLength !== this.bookmarks.length;
    },

    getCodes() {
        return [...this.bookmarks];
    },

    getModules() {
        if (typeof DataManager === 'undefined' || !Array.isArray(DataManager.modules)) {
            return [];
        }
        return this.bookmarks
            .map(code => DataManager.getModule(code))
            .filter(Boolean);
    },

    getCount() {
        return this.bookmarks.length;
    },

    /** Clear the active guest or account bookmark store. */
    async clear() {
        if (this.accountMode) {
            const response = await apiFetch('/api/bookmarks', { method: 'DELETE' });
            if (!response.ok) throw new Error('Could not clear bookmarks.');
        }
        this.bookmarks = [];
        if (!this.accountMode) this.saveLocal();
        this.notify();
    },
};

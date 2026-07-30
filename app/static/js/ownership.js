/**
 * Offer an explicit one-time transfer of this browser's guest activity.
 * @module ownership
 */
(function initialiseOwnershipClaim() {
    if (!window.ModuleGoAuth?.authenticated) return;

    const promptKey = 'modulego_claim_prompted';

    /** Ask before transferring any guest rows or local bookmarks. */
    async function offerClaim() {
        if (sessionStorage.getItem(promptKey) === '1') return;
        if (typeof BookmarkManager !== 'undefined') await BookmarkManager.init();
        const bookmarks = typeof BookmarkManager !== 'undefined'
            ? BookmarkManager.getCodes()
            : [];
        const response = await fetch('/api/ownership/pending');
        if (!response.ok) return;
        const pending = await response.json();
        const total = pending.reviews + pending.votes + bookmarks.length;
        if (!total) return;

        sessionStorage.setItem(promptKey, '1');
        const accepted = window.confirm(
            `Move this browser's guest activity to your account?\n\n` +
            `${pending.reviews} review(s), ${pending.votes} vote(s), ` +
            `${bookmarks.length} bookmark(s).\n\n` +
            'Your existing account content will be kept if there is a conflict.'
        );
        if (!accepted) return;

        const claimResponse = await apiFetch('/api/ownership/claim', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bookmark_codes: bookmarks }),
        });
        if (!claimResponse.ok) {
            sessionStorage.removeItem(promptKey);
            return;
        }
        localStorage.removeItem('moduleGoBookmarks');
        document.dispatchEvent(new CustomEvent('ownership:claimed', {
            detail: await claimResponse.json(),
        }));
        window.location.reload();
    }

    document.addEventListener('DOMContentLoaded', () => {
        offerClaim().catch(error => {
            console.warn('Could not check guest activity:', error);
        });
    });
})();

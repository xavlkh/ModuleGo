/**
 * Shared utility functions for the ModuleGo application.
 * @module utils
 */

/**
 * Fetch a same-origin API and attach CSRF protection to unsafe methods.
 * Guest/account ownership is derived by the server from HTTP-only cookies.
 * @param {string|URL|Request} input - Fetch target.
 * @param {RequestInit} [options={}] - Standard fetch options.
 * @returns {Promise<Response>} Fetch response.
 */
function apiFetch(input, options = {}) {
    const requestOptions = { credentials: 'same-origin', ...options };
    const method = String(requestOptions.method || 'GET').toUpperCase();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        const headers = new Headers(requestOptions.headers || {});
        const token = document.querySelector('meta[name="csrf-token"]')?.content;
        if (token) headers.set('X-CSRFToken', token);
        requestOptions.headers = headers;
    }
    return fetch(input, requestOptions);
}

/**
 * Escape HTML special characters to prevent XSS attacks.
 * @param {string|*} value - The value to escape.
 * @returns {string} The escaped HTML string.
 */
function escapeHtml(value) {
    return String(value || '').replace(/[&<>'"]/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
    })[character]);
}

function createStars(rating) {
    const filled = '<i data-lucide="star" class="w-4 h-4 inline-block fill-amber-400 text-amber-400"></i>'.repeat(rating);
    const empty = '<i data-lucide="star" class="w-4 h-4 inline-block text-amber-400"></i>'.repeat(5 - rating);
    return filled + empty;
}

function parseTimestamp(value) {
    if (!value) return null;
    // PostgreSQL returns "YYYY-MM-DD HH:MM:SS" (no T, no TZ). Append T and Z
    // to treat bare timestamps as UTC, preventing timezone-shifted display.
    const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`;
    const date = new Date(normalized);
    return Number.isNaN(date.getTime()) ? null : date;
}

function showMessage(element, message, type) {
    const colorMap = {
        success: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-200 border border-emerald-200 dark:border-emerald-700',
        danger: 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-700'
    };
    element.textContent = message;
    element.className = `mb-4 rounded-lg px-4 py-2.5 text-sm font-medium ${colorMap[type] || colorMap.danger}`;
}

function createReviewActionsHTML(reviewId, isOwner = false) {
    if (!isOwner) return '';
    return `
        <div class="flex gap-1.5 flex-shrink-0">
            <button class="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-200 dark:border-zinc-700 text-zinc-400 dark:text-zinc-400 hover:border-primary-300 dark:hover:border-primary-500 hover:text-primary-500 dark:hover:text-primary-400 transition-all edit-review-btn" type="button" data-review-id="${reviewId}" aria-label="Edit review">
                <i data-lucide="pencil" class="w-3.5 h-3.5"></i>
            </button>
            <button class="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-200 dark:border-zinc-700 text-zinc-400 dark:text-zinc-400 hover:border-red-300 dark:hover:border-red-500 hover:text-red-500 dark:hover:text-red-400 transition-all delete-review-btn" type="button" data-review-id="${reviewId}" aria-label="Delete review">
                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
        </div>
    `;
}

function formatReviewDate(date) {
    const dd = String(date.getDate()).padStart(2, '0');
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const yy = String(date.getFullYear()).slice(-2);
    let hours = date.getHours();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    const hh = String(hours).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    const ss = String(date.getSeconds()).padStart(2, '0');
    return `${dd}/${mm}/${yy} ${hh}:${min}:${ss} ${ampm}`;
}

/**
 * Handle a vote action on a review (shared by detail.js and reviews.js).
 * @param {number} reviewId - The review to vote on.
 * @param {number} voteType - 1 for upvote, -1 for downvote.
 * @param {string} articleSelector - CSS selector to find the review's container.
 */
async function handleVote(reviewId, voteType, articleSelector) {
    const article = document.querySelector(articleSelector);
    const btn = article?.querySelector(`.vote-btn[data-vote="${voteType}"]`);
    if (btn) btn.disabled = true;
    try {
        const response = await apiFetch(`/api/reviews/${reviewId}/vote`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ vote_type: voteType }),
        });
        if (!response.ok) throw new Error('Failed to vote.');
        if (!article) return;

        const votesResponse = await fetch(`/api/reviews/${reviewId}/vote`);
        if (!votesResponse.ok) return;
        const votes = await votesResponse.json();

        const scoreEl = article.querySelector('.vote-score');
        if (scoreEl) scoreEl.textContent = votes.score;

        const upBtn = article.querySelector('.vote-btn[data-vote="1"]');
        const downBtn = article.querySelector('.vote-btn[data-vote="-1"]');
        if (upBtn) {
            const upIcon = upBtn.querySelector('i') || upBtn.querySelector('svg');
            if (upIcon) {
                if (votes.user_vote === 1) {
                    upIcon.setAttribute('class', 'w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400 fill-emerald-500');
                    upBtn.classList.add('bg-emerald-500/10');
                } else {
                    upIcon.setAttribute('class', 'w-3.5 h-3.5 text-zinc-400 dark:text-zinc-500 hover:text-emerald-500 dark:hover:text-emerald-400');
                    upBtn.classList.remove('bg-emerald-500/10');
                }
            }
        }
        if (downBtn) {
            const downIcon = downBtn.querySelector('i') || downBtn.querySelector('svg');
            if (downIcon) {
                if (votes.user_vote === -1) {
                    downIcon.setAttribute('class', 'w-3.5 h-3.5 text-red-500 dark:text-red-400 fill-red-500');
                    downBtn.classList.add('bg-red-500/10');
                } else {
                    downIcon.setAttribute('class', 'w-3.5 h-3.5 text-zinc-400 dark:text-zinc-500 hover:text-red-500 dark:hover:text-red-400');
                    downBtn.classList.remove('bg-red-500/10');
                }
            }
        }
    } catch (error) {
        console.error('Error voting:', error);
    } finally {
        if (btn) btn.disabled = false;
    }
}

function createVoteButtonsHTML(reviewId, votes, isOwnReview) {
    const upActive = votes.user_vote === 1;
    const downActive = votes.user_vote === -1;
    const upClass = upActive
        ? 'text-emerald-500 dark:text-emerald-400 fill-emerald-500'
        : 'text-zinc-400 dark:text-zinc-500 hover:text-emerald-500 dark:hover:text-emerald-400';
    const downClass = downActive
        ? 'text-red-500 dark:text-red-400 fill-red-500'
        : 'text-zinc-400 dark:text-zinc-500 hover:text-red-500 dark:hover:text-red-400';
    const upBtn = upActive ? 'bg-emerald-500/10' : '';
    const downBtn = downActive ? 'bg-red-500/10' : '';
    const disabled = isOwnReview ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer';
    const attr = isOwnReview ? 'disabled' : '';

    return `
        <button class="vote-btn p-1.5 rounded-lg transition-colors ${disabled} ${upBtn}" data-review-id="${reviewId}" data-vote="1" ${attr} title="Upvote">
            <i data-lucide="thumbs-up" class="w-3.5 h-3.5 ${upClass}"></i>
        </button>
        <span class="vote-score text-xs font-semibold text-zinc-600 dark:text-zinc-300 min-w-[1rem] text-center">${votes.score}</span>
        <button class="vote-btn p-1.5 rounded-lg transition-colors ${disabled} ${downBtn}" data-review-id="${reviewId}" data-vote="-1" ${attr} title="Downvote">
            <i data-lucide="thumbs-down" class="w-3.5 h-3.5 ${downClass}"></i>
        </button>`;
}

function createModalController({ overlayId, closeBtnId, cancelBtnId }) {
    let panel = null;

    function init() {
        panel = document.getElementById(overlayId);
        const closeBtn = document.getElementById(closeBtnId);
        const cancelBtn = cancelBtnId ? document.getElementById(cancelBtnId) : null;

        if (panel) {
            panel.addEventListener('click', (e) => {
                if (e.target === panel) hide();
            });
        }
        if (closeBtn) closeBtn.addEventListener('click', hide);
        if (cancelBtn) cancelBtn.addEventListener('click', hide);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') hide();
        });
    }

    function show() {
        if (panel) {
            panel.classList.remove('hidden');
            // Lock body scroll while modal is open
            document.body.style.overflow = 'hidden';
        }
    }

    function hide() {
        if (panel) {
            panel.classList.add('hidden');
            // Restore body scroll when modal closes
            document.body.style.overflow = '';
        }
    }

    return { show, hide, init };
}

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

/**
 * Account profile page: password change and account deletion.
 * @module profile
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('deleteAccountForm');
    if (!form) return;

    const passwordInput = form.querySelector('[name="current_password"]');
    const tokenInput = document.getElementById('deleteAccountToken');
    const submitButton = document.getElementById('deleteAccountButton');
    const errorMessage = document.getElementById('deleteAccountError');

    const showError = (message) => {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    };

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        errorMessage.classList.add('hidden');
        submitButton.disabled = true;

        try {
            const response = await fetch(form.dataset.verifyUrl, {
                method: 'POST',
                body: new FormData(form),
                headers: { Accept: 'application/json' },
            });
            const result = await response.json();
            if (!response.ok || !result.verified) {
                showError(result.message || 'Could not verify your password.');
                return;
            }

            if (!window.confirm('Delete this account permanently?')) return;

            tokenInput.value = result.confirmation_token;
            passwordInput.value = '';
            form.action = form.dataset.deleteUrl;
            HTMLFormElement.prototype.submit.call(form);
        } catch (_error) {
            showError('Could not verify your password. Please try again.');
        } finally {
            submitButton.disabled = false;
        }
    });
});

/**
 * Share and export functionality for filtered module lists.
 * Handles URL sharing and CSV export.
 * @module share
 */
const ShareManager = {
    getShareUrl() {
        const params = new URLSearchParams(window.location.search);
        const school = document.getElementById('schoolFilter')?.value || 'all';
        const diploma = document.getElementById('diplomaFilter')?.value || 'all';
        const minor = document.getElementById('minorFilter')?.value || 'all';
        const rating = document.getElementById('ratingFilter')?.value || 'all';
        const career = document.getElementById('careerFilter')?.value || 'all';
        const q = document.getElementById('searchInput')?.value || '';

        if (q) params.set('q', q);
        if (school !== 'all') params.set('school', school);
        else params.delete('school');
        if (diploma !== 'all') params.set('diploma', diploma);
        else params.delete('diploma');
        if (minor !== 'all') params.set('minor', minor);
        else params.delete('minor');
        if (rating !== 'all') params.set('rating', rating);
        else params.delete('rating');
        if (career !== 'all') params.set('career', career);
        else params.delete('career');

        return `${window.location.origin}${window.location.pathname}?${params.toString()}`;
    },

    async copyLink(btn) {
        const url = this.getShareUrl();
        try {
            await navigator.clipboard.writeText(url);
        } catch {
            const input = document.createElement('input');
            input.value = url;
            document.body.appendChild(input);
            input.select();
            document.execCommand('copy');
            document.body.removeChild(input);
        }
        history.replaceState(null, '', url);
        if (btn) {
            const original = btn.innerHTML;
            btn.innerHTML = '<i data-lucide="check" class="h-3.5 w-3.5"></i>Copied!';
            btn.disabled = true;
            lucide.createIcons();
            setTimeout(() => {
                btn.innerHTML = original;
                btn.disabled = false;
                lucide.createIcons();
            }, 2000);
        }
    },

    exportCSV() {
        if (!DataManager || !DataManager.modules || DataManager.modules.length === 0) {
            this.showToast('No modules to export');
            return;
        }

        const headers = ['Code', 'Name', 'School', 'Synopsis', 'URL', 'Diplomas', 'Minors'];
        const rows = DataManager.modules.map(m => {
            const rawDiplomas = DataManager.getDiplomasByModule(m.code);
            const merged = new Map();
            for (const d of rawDiplomas) {
                const key = `${d.course_code}||${d.category}`;
                if (merged.has(key)) {
                    const existing = merged.get(key);
                    if (d.major_name && !existing.majorNames.includes(d.major_name)) {
                        existing.majorNames.push(d.major_name);
                    }
                } else {
                    merged.set(key, { ...d, majorNames: d.major_name ? [d.major_name] : [] });
                }
            }
            const diplomas = [...merged.values()];
            const diplomaStr = diplomas.map(d => {
                if (d.category === 'Major' && d.majorNames.length > 0) {
                    return `${d.course_code} (Major: ${d.majorNames.join('; ')})`;
                }
                return `${d.course_code} (${d.category})`;
            }).join('; ');
            const minors = DataManager.getMinorsByModule(m.code);
            const minorStr = minors.map(min => min.minor_name).join('; ');
            return [
                `"${m.code}"`,
                `"${(m.name || '').replace(/"/g, '""')}"`,
                `"${m.school || ''}"`,
                `"${(m.synopsis || '').replace(/"/g, '""')}"`,
                `"${m.url || ''}"`,
                `"${diplomaStr.replace(/"/g, '""')}"`,
                `"${minorStr.replace(/"/g, '""')}"`,
            ].join(',');
        });

        const csv = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `modulego-modules-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        this.showToast(`Exported ${DataManager.modules.length} modules`);
    },

    showToast(msg) {
        let toast = document.getElementById('share-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'share-toast';
            toast.className = 'fixed bottom-20 left-1/2 -translate-x-1/2 z-[10001] rounded-full bg-zinc-800 dark:bg-zinc-700 text-white px-4 py-2.5 text-sm shadow-lg transition-all duration-300';
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.style.opacity = '1';
        setTimeout(() => { toast.style.opacity = '0'; }, 2500);
    },
};

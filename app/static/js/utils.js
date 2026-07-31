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
            document.body.style.overflow = 'hidden';
        }
    }

    function hide() {
        if (panel) {
            panel.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }

    return { show, hide, init };
}

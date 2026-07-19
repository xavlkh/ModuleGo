/**
 * Shared utility functions for the ModuleGo application.
 * @module utils
 */

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

/**
 * Generate star rating HTML markup.
 * @param {number} rating - The rating value (1-5).
 * @returns {string} HTML string with filled and empty stars.
 */
function createStars(rating) {
    const filled = '<i data-lucide="star" class="w-4 h-4 inline-block fill-amber-400 text-amber-400"></i>'.repeat(rating);
    const empty = '<i data-lucide="star" class="w-4 h-4 inline-block text-amber-400"></i>'.repeat(5 - rating);
    return filled + empty;
}

/**
 * Normalize a timestamp string to a Date object.
 * @param {string} value - ISO or space-separated timestamp.
 * @returns {Date|null} Parsed Date or null if invalid.
 */
function parseTimestamp(value) {
    if (!value) return null;
    const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`;
    const date = new Date(normalized);
    return Number.isNaN(date.getTime()) ? null : date;
}

/**
 * Display a status message in an element with appropriate styling.
 * @param {HTMLElement} element - The target element.
 * @param {string} message - The message text.
 * @param {'success'|'danger'} type - The message type.
 */
function showMessage(element, message, type) {
    const colorMap = {
        success: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-200 border border-emerald-200 dark:border-emerald-700',
        danger: 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-700'
    };
    element.textContent = message;
    element.className = `mb-4 rounded-lg px-4 py-2.5 text-sm font-medium ${colorMap[type] || colorMap.danger}`;
}

/**
 * Generate HTML for review edit/delete action buttons.
 * @param {number} reviewId - The review ID.
 * @returns {string} HTML string for the action buttons.
 */
function createReviewActionsHTML(reviewId) {
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

/**
 * Format a date as DD/MM/YY HH:MM.
 * @param {Date} date - The date to format.
 * @returns {string} Formatted date string.
 */
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
 * Create a modal controller with show/hide/init methods.
 * @param {Object} config - Configuration object.
 * @param {string} config.overlayId - The modal overlay element ID.
 * @param {string} config.closeBtnId - The close button element ID.
 * @param {string} [config.cancelBtnId] - Optional cancel button element ID.
 * @returns {{show: Function, hide: Function, init: Function}} Modal controller.
 */
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

/**
 * Powers the all-module review dashboard: lists, filters, sorts, and
 * provides edit/delete via a modal.
 * @module reviews
 */

const ReviewDashboard = {
    /** @type {Array<Object>} All reviews from /api/reviews. */
    reviews: [],
    /** @type {number|null} ID of the review being edited, or null. */
    editingReviewId: null,
    /** @type {Object<string, HTMLElement>} Cached DOM element references. */
    elements: {},
    /** @type {{show: Function, hide: Function, init: Function}|null} Edit review modal controller. */
    modal: null,

    /**
     * Bootstrap the dashboard: cache elements, bind events, load data.
     */
    async init() {
        this.cacheElements();
        this.bindEvents();
        this.modal = createModalController({
            overlayId: 'editReviewModalOverlay',
            closeBtnId: 'editReviewModalClose',
            cancelBtnId: 'editReviewCancelBtn',
        });
        this.modal.init();

        try {
            await Promise.all([DataManager.loadData(), this.loadReviews()]);
            this.initFromURL();
            this._toggleClearBtn();
            this._updateFilterToggleActive();
            this.render();
        } catch (error) {
            console.error('Could not initialize review dashboard:', error);
            this.elements.list.innerHTML = '<p class="text-red-500 dark:text-red-400 py-8 text-center">Could not load the review dashboard.</p>';
        }
    },

    /**
     * Cache frequently accessed DOM elements to avoid repeated queries.
     */
    cacheElements() {
        this.elements = {
            list: document.getElementById('reviewDashboardList'),
            search: document.getElementById('reviewSearch'),
            clearSearch: document.getElementById('clearreviewSearch'),
            confidenceFilter: document.getElementById('confidenceFilter'),
            ratingFilter: document.getElementById('ratingFilter'),
            sort: document.getElementById('reviewSort'),
            confidenceFilterMobile: document.getElementById('confidenceFilterMobile'),
            ratingFilterMobile: document.getElementById('ratingFilterMobile'),
            sortMobile: document.getElementById('reviewSortMobile'),
            clearFiltersMobile: document.getElementById('clearReviewFiltersMobile'),
            resultCount: document.getElementById('dashboardResultCount'),
            reviewCount: document.getElementById('dashboardReviewCount'),
            monthlyReviewCount: document.getElementById('dashboardMonthlyReviewCount'),
            moduleCount: document.getElementById('dashboardModuleCount'),
            message: document.getElementById('dashboardMessage'),
            editMessage: document.getElementById('dashboardEditMessage'),
            editModule: document.getElementById('editReviewModule'),
            editRating: document.getElementById('editReviewRating'),
            editComment: document.getElementById('editReviewComment'),
            editAnonymous: document.getElementById('editReviewAnonymous'),
            saveButton: document.getElementById('saveDashboardReviewBtn'),
            clearFilters: document.getElementById('clearReviewFilters'),
            filterToggle: document.getElementById('reviewFilterToggle'),
            filterPanel: document.getElementById('reviewFilterPanel'),
        };
    },

    /**
     * Attach event listeners to the search, filter, sort, and save controls.
     */
    bindEvents() {
        this._toggleClearBtn = () => {
            if (!this.elements.clearSearch) return;
            this.elements.clearSearch.classList.toggle('hidden', !this.elements.search.value);
            this.elements.clearSearch.classList.toggle('flex', !!this.elements.search.value);
        };
        this._toggleClearBtn();
        this.elements.search.addEventListener('input', () => { this._toggleClearBtn(); this.updateURL(); this.renderReviews(); });
        this.elements.clearSearch.addEventListener('click', () => {
            this.elements.search.value = '';
            this._toggleClearBtn();
            this.updateURL();
            this.renderReviews();
            this.elements.search.focus();
        });

        const onFilterChange = () => { this.updateSelectActiveStates(); this._updateFilterToggleActive(); this.updateURL(); this.renderReviews(); };
        this.elements.confidenceFilter.addEventListener('change', onFilterChange);
        this.elements.ratingFilter.addEventListener('change', onFilterChange);
        this.elements.sort.addEventListener('change', onFilterChange);

        if (this.elements.confidenceFilterMobile) {
            this.elements.confidenceFilterMobile.addEventListener('change', () => {
                this.elements.confidenceFilter.value = this.elements.confidenceFilterMobile.value;
                onFilterChange();
            });
        }
        if (this.elements.ratingFilterMobile) {
            this.elements.ratingFilterMobile.addEventListener('change', () => {
                this.elements.ratingFilter.value = this.elements.ratingFilterMobile.value;
                onFilterChange();
            });
        }
        if (this.elements.sortMobile) {
            this.elements.sortMobile.addEventListener('change', () => {
                this.elements.sort.value = this.elements.sortMobile.value;
                onFilterChange();
            });
        }

        this.elements.saveButton.addEventListener('click', () => this.saveEdit());
        if (this.elements.clearFilters) this.elements.clearFilters.addEventListener('click', () => this.clearFilters());
        if (this.elements.clearFiltersMobile) this.elements.clearFiltersMobile.addEventListener('click', () => this.clearFilters());

        if (this.elements.filterToggle && this.elements.filterPanel) {
            this.elements.filterToggle.addEventListener('click', () => {
                const isClosed = this.elements.filterPanel.style.gridTemplateRows === '0fr';
                this.elements.filterPanel.style.gridTemplateRows = isClosed ? '1fr' : '0fr';
            });
        }
    },

    _updateFilterToggleActive() {
        const btn = this.elements.filterToggle;
        if (!btn) return;
        const hasActive = this.elements.confidenceFilter.value !== 'all' ||
                          this.elements.ratingFilter.value !== 'all' ||
                          this.elements.sort.value !== 'newest';
        const ACTIVE = ['bg-emerald-500/10', 'dark:bg-emerald-500/20', 'border-emerald-300', 'dark:border-emerald-700', 'text-emerald-600', 'dark:text-emerald-400'];
        const IDLE = ['bg-white/95', 'dark:bg-zinc-800', 'border-zinc-200', 'dark:border-zinc-700', 'text-zinc-600', 'dark:text-zinc-300'];
        (hasActive ? IDLE : ACTIVE).forEach(c => btn.classList.remove(c));
        (hasActive ? ACTIVE : IDLE).forEach(c => btn.classList.add(c));
    },

    updateSelectActiveStates() {
        const selects = [this.elements.confidenceFilter, this.elements.ratingFilter, this.elements.sort,
                         this.elements.confidenceFilterMobile, this.elements.ratingFilterMobile, this.elements.sortMobile];
        selects.forEach(s => {
            if (!s) return;
            const isDefault = s.id.includes('Sort') || s.id.includes('sort') ? s.value === 'newest' : s.value === 'all';
            if (!isDefault) {
                s.classList.add('select-field-active');
            } else {
                s.classList.remove('select-field-active');
            }
        });
    },

    updateURL() {
        const url = new URL(window.location);
        const search = this.elements.search.value.trim();
        const confidence = this.elements.confidenceFilter.value;
        const rating = this.elements.ratingFilter.value;
        const sort = this.elements.sort.value;

        const setParam = (key, value, def) => {
            if (value && value !== def) url.searchParams.set(key, value);
            else url.searchParams.delete(key);
        };
        setParam('q', search, '');
        setParam('confidence', confidence, 'all');
        setParam('rating', rating, 'all');
        setParam('sort', sort, 'newest');
        window.history.replaceState({}, '', url);
    },

    initFromURL() {
        const params = new URLSearchParams(window.location.search);
        const q = params.get('q') || '';
        const confidence = params.get('confidence') || 'all';
        const rating = params.get('rating') || 'all';
        const sort = params.get('sort') || 'newest';

        if (q) this.elements.search.value = q;
        if (confidence !== 'all') {
            this.elements.confidenceFilter.value = confidence;
            if (this.elements.confidenceFilterMobile) this.elements.confidenceFilterMobile.value = confidence;
        }
        if (rating !== 'all') {
            this.elements.ratingFilter.value = rating;
            if (this.elements.ratingFilterMobile) this.elements.ratingFilterMobile.value = rating;
        }
        if (sort !== 'newest') {
            this.elements.sort.value = sort;
            if (this.elements.sortMobile) this.elements.sortMobile.value = sort;
        }
    },

    clearFilters() {
        this.elements.confidenceFilter.value = 'all';
        this.elements.ratingFilter.value = 'all';
        this.elements.sort.value = 'newest';
        if (this.elements.confidenceFilterMobile) this.elements.confidenceFilterMobile.value = 'all';
        if (this.elements.ratingFilterMobile) this.elements.ratingFilterMobile.value = 'all';
        if (this.elements.sortMobile) this.elements.sortMobile.value = 'newest';
        this.updateSelectActiveStates();
        this._updateFilterToggleActive();
        this.updateURL();
        this.renderReviews();
    },

    /**
     * Fetch all reviews from the API.
     * @throws {Error} If the response is not OK.
     */
    async loadReviews() {
        const response = await fetch('/api/reviews');
        if (!response.ok) throw new Error('Failed to load reviews.');
        this.reviews = await response.json();
    },

    /**
     * Render stats and the review list.
     */
    async render() {
        this.renderStats();
        await this.renderReviews();
        this.updateSelectActiveStates();
    },

    /**
     * Update the stat cards (total reviews, this month, modules rated).
     */
    renderStats() {
        const count = this.reviews.length;
        const modulesRated = new Set(this.reviews.map(r => r.module_code)).size;
        const now = new Date();
        const monthlyCount = this.reviews.filter(r => {
            const d = parseTimestamp(r.created_at);
            return d && d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
        }).length;

        this.elements.reviewCount.textContent = String(count);
        this.elements.monthlyReviewCount.textContent = String(monthlyCount);
        this.elements.moduleCount.textContent = String(modulesRated);
    },

    /**
     * Determine the confidence level for a module based on its review count.
     * @param {string} moduleCode - The module code to check.
     * @returns {'high'|'medium'|'low'} The confidence level.
     */
    getConfidence(moduleCode) {
        const summary = DataManager.getRatingSummary(moduleCode);
        const count = summary.review_count || 0;
        const allRatings = DataManager.ratings || {};
        const allCounts = Object.values(allRatings).map(r => r.review_count || 0);
        if (allCounts.length === 0) return 'low';
        const maxCount = Math.max(...allCounts);
        if (maxCount === 0) return 'low';
        if (count >= maxCount) return 'high';
        return 'low';
    },

    /**
     * Get the display label and styles for a confidence level.
     * @param {'high'|'medium'|'low'} level - The confidence level.
     * @returns {{label: string, classes: string}} Label and Tailwind classes.
     */
    getConfidenceStyle(level) {
        const styles = {
            high: { label: 'High confidence', classes: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-700' },
            medium: { label: 'Medium confidence', classes: 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-700' },
            low: { label: 'Low confidence', classes: 'bg-zinc-50 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700' },
        };
        return styles[level];
    },

    getFilteredReviews() {
        const query = this.elements.search.value.trim().toLowerCase();
        const confidence = this.elements.confidenceFilter.value;
        const rating = this.elements.ratingFilter.value;

        const filtered = this.reviews.filter(review => {
            const module = DataManager.getModule(review.module_code);
            const searchable = [review.module_code, module ? module.name : '', review.comment].join(' ').toLowerCase();
            const matchesQuery = !query || searchable.includes(query);
            const matchesRating = rating === 'all' || review.rating === Number(rating);
            const matchesConfidence = confidence === 'all' || this.getConfidence(review.module_code) === confidence;
            return matchesQuery && matchesRating && matchesConfidence;
        });

        const dir = this.elements.sort.value === 'oldest' ? 1 : -1;
        return filtered.sort((a, b) => {
            const aTime = parseTimestamp(a.created_at)?.getTime() || 0;
            const bTime = parseTimestamp(b.created_at)?.getTime() || 0;
            return (aTime - bTime) * dir;
        });
    },

    /**
     * Render the filtered review list, or an empty state if none match.
     */
    async renderReviews() {
        const filtered = this.getFilteredReviews();
        const label = filtered.length === 1 ? 'review' : 'reviews';
        this.elements.resultCount.textContent = `${filtered.length} ${label}`;
        this.elements.list.innerHTML = '';

        if (filtered.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'py-16 text-center';
            empty.innerHTML = `
                <div class="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-100 dark:bg-zinc-800 mb-4">
                    <i data-lucide="message-square" class="w-8 h-8 text-zinc-400 dark:text-zinc-400"></i>
                </div>
                <h3 class="text-lg font-semibold text-zinc-700 dark:text-zinc-300 mb-1">No reviews found</h3>
                <p class="text-sm text-zinc-500 dark:text-zinc-400">Try a different search or rating filter.</p>
            `;
            this.elements.list.appendChild(empty);
            lucide.createIcons();
            return;
        }

        let votesData = {};
        try {
            const reviewIds = filtered.map(r => r.id);
            const votesResponse = await apiFetch('/api/reviews/votes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ review_ids: reviewIds }),
            });
            if (votesResponse.ok) {
                votesData = await votesResponse.json();
            }
        } catch (e) {
            console.warn('Could not load vote data:', e);
        }

        filtered.forEach(r => this.elements.list.appendChild(this.createReviewCard(r, votesData[r.id] || { score: 0, user_vote: 0 })));
        lucide.createIcons();
    },

createReviewCard(review, votes = { score: 0, user_vote: 0 }) {
    const module = DataManager.getModule(review.module_code);
    const isOwner = review.is_owner === true;

    const article = document.createElement('article');
    article.className = 'glass-card p-5';
    article.dataset.reviewId = review.id;

    article.innerHTML = `
        <div class="flex items-start justify-between gap-3 mb-3">
            <div>
                <span class="text-xs font-bold uppercase tracking-wider text-primary-500 dark:text-primary-400">${escapeHtml(review.module_code)}</span>
                <h3 class="text-base font-bold text-zinc-900 dark:text-white mb-1">${module ? escapeHtml(module.name) : 'Module name unavailable'}</h3>
                <div class="star-rating flex gap-0.5 text-sm" aria-label="${review.rating} out of 5 stars">
                    ${createStars(review.rating)}
                </div>
            </div>
            ${createReviewActionsHTML(review.id, isOwner)}
        </div>
        <div class="rounded-lg bg-zinc-50 dark:bg-zinc-800/60 pl-3 py-2 mb-3">
            <p class="mb-1 text-xs font-semibold text-zinc-500 dark:text-zinc-400">${escapeHtml(review.author?.label || 'Anonymous student')}</p>
            <p class="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">${review.comment ? escapeHtml(review.comment) : 'No written comment'}</p>
        </div>
        <div class="flex items-center gap-3">
            <small class="text-xs text-zinc-400 dark:text-zinc-400">${this.formatDate(review)}</small>
            <div class="flex items-center gap-1 ml-auto">
                ${createVoteButtonsHTML(review.id, votes, isOwner)}
            </div>
        </div>
    `;

        if (!review.comment) {
            article.querySelector('.text-sm.text-zinc-700').classList.add('text-zinc-400', 'dark:text-zinc-400', 'italic');
        }
        const editBtn = article.querySelector('.edit-review-btn');
        const deleteBtn = article.querySelector('.delete-review-btn');
        if (editBtn) editBtn.addEventListener('click', () => this.openEdit(review.id));
        if (deleteBtn) deleteBtn.addEventListener('click', () => this.deleteReview(review.id));

        // Add vote button handlers
        article.querySelectorAll('.vote-btn').forEach(btn => {
            btn.addEventListener('click', () => this.handleVote(Number(btn.dataset.reviewId), Number(btn.dataset.vote)));
        });

        return article;
    },

    /**
     * Handle a vote action on a review.
     * @param {number} reviewId - The review to vote on.
     * @param {number} voteType - 1 for upvote, -1 for downvote.
     */
    async handleVote(reviewId, voteType) {
        return handleVote(reviewId, voteType, `article[data-review-id="${reviewId}"]`);
    },

    /**
     * Open the edit modal and populate it with the selected review's data.
     * @param {number} reviewId - The review to edit.
     */
    openEdit(reviewId) {
        const review = this.reviews.find(r => r.id === reviewId);
        if (!review) return;
        const module = DataManager.getModule(review.module_code);

        this.editingReviewId = reviewId;
        this.elements.editModule.textContent = `${review.module_code} - ${module ? module.name : 'Module'}`;
        this.elements.editRating.value = String(review.rating);
        this.elements.editComment.value = review.comment;
        if (this.elements.editAnonymous) {
            this.elements.editAnonymous.checked = review.author?.anonymous !== false;
        }
        this.clearEditMessage();
        this.modal.show();
    },

    /**
     * Save the edited review from the modal form.
     */
    async saveEdit() {
        if (this.editingReviewId === null) return;
        this.elements.saveButton.disabled = true;
        this.elements.saveButton.textContent = 'Saving...';

        try {
            const payload = {
                rating: Number(this.elements.editRating.value),
                comment: this.elements.editComment.value.trim(),
            };
            if (this.elements.editAnonymous) {
                payload.is_anonymous = this.elements.editAnonymous.checked;
            }
            const response = await apiFetch(`/api/reviews/${this.editingReviewId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok) {
                this.showEditMessage(result.error || 'Could not update review.');
                return;
            }
            await this.refresh();
            this.modal.hide();
            showMessage(this.elements.message, 'Review updated.', 'success');
        } catch (error) {
            console.error('Could not update review:', error);
            this.showEditMessage('Could not update review. Please try again.');
        } finally {
            this.elements.saveButton.disabled = false;
            this.elements.saveButton.textContent = 'Save Changes';
        }
    },

    /**
     * Delete a review after user confirmation.
     * @param {number} reviewId - The review to delete.
     */
    async deleteReview(reviewId) {
        if (!window.confirm('Delete this review permanently?')) return;
        try {
            const response = await apiFetch(`/api/reviews/${reviewId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Could not delete review.');
            }
            await this.refresh();
            showMessage(this.elements.message, 'Review deleted.', 'success');
        } catch (error) {
            console.error('Could not delete review:', error);
            showMessage(this.elements.message, error.message, 'danger');
        }
    },

    /**
     * Reload reviews and ratings, then re-render the dashboard.
     */
    async refresh() {
        await Promise.all([this.loadReviews(), DataManager.refreshRatingSummaries()]);
        this.render();
    },

    /**
     * Show an error message in the edit modal's message area.
     * @param {string} message - The error message.
     */
    showEditMessage(message) {
        showMessage(this.elements.editMessage, message, 'danger');
    },

    /** Clear the edit modal's message area. */
    clearEditMessage() {
        this.elements.editMessage.textContent = '';
        this.elements.editMessage.className = 'hidden mb-4 rounded-lg px-4 py-2.5 text-sm';
    },

    /**
     * Format a review's date for display (Submitted/Updated prefix).
     * @param {Object} review - The review object.
     * @returns {string} Formatted date string.
     */
    formatDate(review) {
        const value = review.updated_at || review.created_at;
        if (!value) return '';
        const date = parseTimestamp(value);
        const prefix = review.updated_at ? 'Updated ' : 'Submitted ';
        return prefix + (date ? formatReviewDate(date) : value);
    },
};

document.addEventListener('DOMContentLoaded', () => ReviewDashboard.init());

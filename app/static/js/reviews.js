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
            confidenceFilter: document.getElementById('confidenceFilter'),
            ratingFilter: document.getElementById('ratingFilter'),
            sort: document.getElementById('reviewSort'),
            resultCount: document.getElementById('dashboardResultCount'),
            reviewCount: document.getElementById('dashboardReviewCount'),
            monthlyReviewCount: document.getElementById('dashboardMonthlyReviewCount'),
            moduleCount: document.getElementById('dashboardModuleCount'),
            message: document.getElementById('dashboardMessage'),
            editMessage: document.getElementById('dashboardEditMessage'),
            editModule: document.getElementById('editReviewModule'),
            editRating: document.getElementById('editReviewRating'),
            editComment: document.getElementById('editReviewComment'),
            saveButton: document.getElementById('saveDashboardReviewBtn'),
        };
    },

    /**
     * Attach event listeners to the search, filter, sort, and save controls.
     */
    bindEvents() {
        this.elements.search.addEventListener('input', () => this.renderReviews());
        this.elements.confidenceFilter.addEventListener('change', () => this.renderReviews());
        this.elements.ratingFilter.addEventListener('change', () => this.renderReviews());
        this.elements.sort.addEventListener('change', () => this.renderReviews());
        this.elements.saveButton.addEventListener('click', () => this.saveEdit());
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

    /**
     * Apply search, confidence, rating, and sort filters to the full review list.
     * @returns {Array<Object>} Filtered and sorted reviews.
     */
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

        // Fetch vote data for all reviews
        let votesData = {};
        try {
            const reviewIds = filtered.map(r => r.id);
            const votesResponse = await fetch('/api/reviews/votes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Owner-Token': getOwnerToken() },
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

    /**
     * Create a single review card DOM element.
     * @param {Object} review - The review object.
     * @param {Object} votes - Vote data {score, user_vote} for this review.
     * @returns {HTMLArticleElement} The card element.
     */
    createReviewCard(review, votes = { score: 0, user_vote: 0 }) {
        const module = DataManager.getModule(review.module_code);
        const isOwner = review.owner_token && review.owner_token === getOwnerToken();
        const isOwnReview = isOwner;

        const upvoteActive = votes.user_vote === 1;
        const downvoteActive = votes.user_vote === -1;
        const upvoteClass = upvoteActive
            ? 'text-emerald-500 dark:text-emerald-400 fill-emerald-500'
            : 'text-zinc-400 dark:text-zinc-500 hover:text-emerald-500 dark:hover:text-emerald-400';
        const downvoteClass = downvoteActive
            ? 'text-red-500 dark:text-red-400 fill-red-500'
            : 'text-zinc-400 dark:text-zinc-500 hover:text-red-500 dark:hover:text-red-400';
        const upvoteBtnClass = upvoteActive ? 'bg-emerald-500/10' : '';
        const downvoteBtnClass = downvoteActive ? 'bg-red-500/10' : '';

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
                <p class="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">${review.comment ? escapeHtml(review.comment) : 'No written comment'}</p>
            </div>
            <div class="flex items-center gap-3">
                <small class="text-xs text-zinc-400 dark:text-zinc-400">${this.formatDate(review)}</small>
                <div class="flex items-center gap-1 ml-auto">
                    <button class="vote-btn p-1.5 rounded-lg transition-colors ${isOwnReview ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'} ${upvoteBtnClass}" data-review-id="${review.id}" data-vote="1" ${isOwnReview ? 'disabled' : ''} title="Upvote">
                        <i data-lucide="thumbs-up" class="w-3.5 h-3.5 ${upvoteClass}"></i>
                    </button>
                    <span class="vote-score text-xs font-semibold text-zinc-600 dark:text-zinc-300 min-w-[1rem] text-center">${votes.score}</span>
                    <button class="vote-btn p-1.5 rounded-lg transition-colors ${isOwnReview ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'} ${downvoteBtnClass}" data-review-id="${review.id}" data-vote="-1" ${isOwnReview ? 'disabled' : ''} title="Downvote">
                        <i data-lucide="thumbs-down" class="w-3.5 h-3.5 ${downvoteClass}"></i>
                    </button>
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
        const article = document.querySelector(`article[data-review-id="${reviewId}"]`);
        const btn = article?.querySelector(`.vote-btn[data-vote="${voteType}"]`);
        if (btn) btn.disabled = true;
        try {
            const response = await fetch(`/api/reviews/${reviewId}/vote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Owner-Token': getOwnerToken() },
                body: JSON.stringify({ vote_type: voteType }),
            });
            if (!response.ok) throw new Error('Failed to vote.');
            if (!article) return;

            const votesResponse = await fetch(`/api/reviews/${reviewId}/vote`, {
                headers: { 'X-Owner-Token': getOwnerToken() },
            });
            if (!votesResponse.ok) return;
            const votes = await votesResponse.json();

            // Update vote buttons and score
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
            // Re-enable button
            if (btn) btn.disabled = false;
        }
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
            const response = await fetch(`/api/reviews/${this.editingReviewId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'X-Owner-Token': getOwnerToken() },
                body: JSON.stringify({
                    rating: Number(this.elements.editRating.value),
                    comment: this.elements.editComment.value.trim(),
                }),
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
            const response = await fetch(`/api/reviews/${reviewId}`, {
                method: 'DELETE',
                headers: { 'X-Owner-Token': getOwnerToken() },
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

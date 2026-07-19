/**
 * Shows module details and manages the review lifecycle in the detail modal.
 * @module detail
 */
const DetailManager = {
    currentModuleCode: null,
    currentReviews: new Map(),
    editingReviewId: null,
    modal: null,

    init() {
        this.modal = createModalController({
            overlayId: 'moduleModalOverlay',
            closeBtnId: 'moduleModalClose'
        });
        this.modal.init();
    },

    showModal() { this.modal.show(); },
    hideModal() { this.modal.hide(); },

    showModuleDetail(moduleCode) {
        const module = DataManager.getModule(moduleCode);
        if (!module) return;

        this.currentModuleCode = module.code;
        this.editingReviewId = null;

        document.getElementById('moduleModalLabel').textContent = `${module.code} - ${module.name}`;
        document.getElementById('moduleModalBody').innerHTML = this.createDetailContent(module);

        document.getElementById('submitReviewBtn').addEventListener('click', () => this.saveReview(module.code));
        document.getElementById('cancelEditReviewBtn').addEventListener('click', () => this.resetReviewForm());

        this.showModal();
        this.loadReviews(module.code);
        lucide.createIcons();
    },

    createDetailContent(module) {
        const diplomas = DataManager.getDiplomasByModule(module.code);
        const diplomasHTML = diplomas.length > 0
            ? diplomas.map(d => {
                const catColors = {
                    'General': 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
                    'Major': 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
                    'Discipline': 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
                    'Elective': 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
                    'Industry': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                };
                const catClass = catColors[d.category] || 'bg-zinc-100 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300';
                const diplomaUrl = d.url ? escapeHtml(d.url) : '#';
                const targetAttr = d.url ? 'target="_blank" rel="noopener"' : '';
                return `
                <li>
                    <a href="${diplomaUrl}" ${targetAttr} class="flex flex-col gap-1 rounded-lg border border-zinc-100 dark:border-zinc-700 px-4 py-3 bg-white/60 dark:bg-zinc-800/60 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-700/60">
                        <div class="flex items-center justify-between gap-2">
                            <div class="font-semibold text-zinc-900 dark:text-white">${escapeHtml(d.course_name || '')}</div>
                            <span class="flex-shrink-0 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${catClass}">${escapeHtml(d.category)}</span>
                        </div>
                        <div class="text-xs text-zinc-500 dark:text-zinc-400">${escapeHtml(d.course_code || '')} &bull; ${escapeHtml(d.school_name || d.school_abbr || '')}</div>
                    </a>
                </li>`;
            }).join('')
            : `<li class="rounded-lg border border-dashed border-zinc-200 dark:border-zinc-700 px-4 py-6 text-center text-zinc-400 dark:text-zinc-400 text-sm">No diploma information available for this module.</li>`;

        return `
            <div class="module-header rounded-xl p-6 mb-6">
                <div class="text-xs font-bold uppercase tracking-wider text-primary-500 dark:text-primary-400 mb-1">${escapeHtml(module.code)}</div>
                <div class="text-xl font-bold text-zinc-900 dark:text-white mb-2">${escapeHtml(module.name)}</div>
                <div class="text-sm font-medium text-primary-700 dark:text-primary-300">${escapeHtml(module.school || 'School not listed')}</div>
            </div>
            <div class="mb-6">
                <h6 class="text-sm font-bold text-zinc-900 dark:text-white mb-2">Synopsis</h6>
                <p class="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">${escapeHtml(module.synopsis)}</p>
            </div>
            <div class="mb-6">
                <a href="${escapeHtml(module.url || '#')}" target="_blank" rel="noopener" class="btn-outline inline-flex items-center text-sm">
                    <i data-lucide="external-link" class="w-4 h-4 mr-2"></i>Source
                </a>
            </div>
            <div class="mb-6">
                <h6 class="text-sm font-bold text-zinc-900 dark:text-white mb-2">Diplomas offering this module</h6>
                <ul class="grid gap-2">${diplomasHTML}</ul>
            </div>
            <hr class="border-zinc-200 dark:border-zinc-700 my-6">
            <div class="flex flex-wrap items-center justify-between gap-2 mb-4">
                <h6 class="text-sm font-bold text-zinc-900 dark:text-white">Student Reviews</h6>
                <div id="reviewSummary" class="inline-flex items-center gap-1 rounded-full bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 px-3 py-1 text-xs text-amber-700 dark:text-amber-200 font-medium">Loading rating...</div>
            </div>
            <div id="reviewsList" class="mb-6" aria-live="polite">
                <div class="flex items-center gap-2 text-zinc-400 dark:text-zinc-400 text-sm py-4">
                    <div class="h-4 w-4 animate-spin rounded-full border-2 border-primary-500 border-t-transparent"></div>
                    Loading reviews...
                </div>
            </div>
            <div id="reviewFormCard" class="mb-2">
                <h6 id="reviewFormTitle" class="text-sm font-bold text-zinc-900 dark:text-white mb-4">Leave a Review</h6>
                <div id="reviewFormMessage" class="hidden mb-3 rounded-lg px-4 py-2.5 text-sm" role="alert"></div>
                <div class="mb-4">
                    <label for="reviewRating" class="mb-1.5 block text-sm font-semibold text-zinc-700 dark:text-zinc-300">Rating</label>
                    <select id="reviewRating" class="select-field w-full rounded-xl bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 shadow-sm pl-4 pr-10 py-2.5 text-sm text-zinc-700 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-primary-400/50 focus:border-primary-400 cursor-pointer">
                        <option value="5">5 - Excellent</option>
                        <option value="4">4 - Good</option>
                        <option value="3">3 - Average</option>
                        <option value="2">2 - Poor</option>
                        <option value="1">1 - Terrible</option>
                    </select>
                </div>
                <div class="mb-4">
                    <label for="reviewComment" class="mb-1.5 block text-sm font-semibold text-zinc-700 dark:text-zinc-300">Comment</label>
                    <textarea id="reviewComment" class="w-full rounded-xl bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 shadow-sm px-4 py-3 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary-400/50 focus:border-primary-400" rows="3" maxlength="500" placeholder="What did you think of this module?"></textarea>
                    <p class="mt-1.5 text-xs text-zinc-400 dark:text-zinc-400">Optional, maximum 500 characters.</p>
                </div>
                <div class="flex gap-3 pt-1">
                    <button id="submitReviewBtn" class="rounded-xl bg-primary-500 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all duration-300 hover:bg-primary-600 hover:shadow active:tranzinc-y-0" type="button">Submit Review</button>
                    <button id="cancelEditReviewBtn" class="hidden rounded-xl border border-zinc-200 dark:border-zinc-700 px-6 py-3 text-sm font-semibold text-zinc-600 dark:text-zinc-400 transition-all duration-300 hover:border-zinc-300 dark:hover:border-zinc-600 hover:text-zinc-800 dark:hover:text-zinc-200 active:tranzinc-y-0" type="button">Cancel edit</button>
                </div>
            </div>
        `;
    },

    async loadReviews(moduleCode) {
        const reviewsList = document.getElementById('reviewsList');
        if (!reviewsList) return;

        try {
            const response = await fetch(`/api/reviews/${encodeURIComponent(moduleCode)}`);
            if (!response.ok) throw new Error('Failed to fetch reviews.');
            const reviews = await response.json();
            this.currentReviews = new Map(reviews.map(r => [r.id, r]));
            this.renderReviewSummary(reviews);

            if (reviews.length === 0) {
                reviewsList.innerHTML = '<p class="text-sm text-zinc-400 dark:text-zinc-400 py-3">No reviews yet. Be the first!</p>';
                return;
            }

            reviewsList.innerHTML = reviews.map(r => this.createReviewMarkup(r)).join('');
            reviewsList.querySelectorAll('.edit-review-btn').forEach(btn => {
                btn.addEventListener('click', () => this.startEditReview(Number(btn.dataset.reviewId)));
            });
            reviewsList.querySelectorAll('.delete-review-btn').forEach(btn => {
                btn.addEventListener('click', () => this.deleteReview(Number(btn.dataset.reviewId)));
            });
            lucide.createIcons();
        } catch (error) {
            console.error('Error loading reviews:', error);
            reviewsList.innerHTML = '<p class="text-sm text-red-500 py-3">Could not load reviews.</p>';
            this.renderReviewSummary([]);
        }
    },

    createReviewMarkup(review) {
        const comment = review.comment
            ? escapeHtml(review.comment)
            : '<span class="text-zinc-400 dark:text-zinc-400 italic">No written comment</span>';
        const updated = review.updated_at
            ? `<span class="ml-2 text-zinc-400 dark:text-zinc-400">Edited ${formatTimestamp(review.updated_at)}</span>`
            : '';

        return `
            <article class="review-item" data-review-id="${review.id}">
                <div class="flex items-start justify-between gap-3">
                    <div class="flex-1">
                        <div class="star-rating flex gap-0.5 text-sm mb-1.5" aria-label="${review.rating} out of 5 stars">
                            ${createStars(review.rating)}
                        </div>
                        <p class="text-sm text-zinc-700 dark:text-zinc-300 mb-1">${comment}</p>
                        <small class="text-xs text-zinc-400 dark:text-zinc-400">${formatTimestamp(review.created_at)}${updated}</small>
                    </div>
                    ${createReviewActionsHTML(review.id)}
                </div>
            </article>
        `;
    },

    renderReviewSummary(reviews) {
        const summary = document.getElementById('reviewSummary');
        if (!summary) return;
        if (reviews.length === 0) {
            summary.innerHTML = '<i data-lucide="star" class="w-4 h-4 mr-1 inline-block text-amber-400" aria-hidden="true"></i>No ratings yet';
            lucide.createIcons();
            return;
        }
        const avg = reviews.reduce((t, r) => t + r.rating, 0) / reviews.length;
        const label = reviews.length === 1 ? 'review' : 'reviews';
        summary.innerHTML = `<i data-lucide="star" class="w-4 h-4 mr-1 inline-block fill-amber-400 text-amber-400" aria-hidden="true"></i><strong>${avg.toFixed(1)}</strong> (${reviews.length} ${label})`;
        lucide.createIcons();
    },

    startEditReview(reviewId) {
        const review = this.currentReviews.get(reviewId);
        if (!review) return;
        this.editingReviewId = reviewId;
        document.getElementById('reviewFormTitle').textContent = 'Edit Review';
        document.getElementById('reviewRating').value = String(review.rating);
        document.getElementById('reviewComment').value = review.comment;
        document.getElementById('submitReviewBtn').textContent = 'Save Changes';
        document.getElementById('cancelEditReviewBtn').classList.remove('hidden');
        clearElementMessage('reviewFormMessage');
        document.getElementById('reviewFormCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    resetReviewForm() {
        this.editingReviewId = null;
        document.getElementById('reviewFormTitle').textContent = 'Leave a Review';
        document.getElementById('reviewRating').value = '5';
        document.getElementById('reviewComment').value = '';
        document.getElementById('submitReviewBtn').textContent = 'Submit Review';
        document.getElementById('cancelEditReviewBtn').classList.add('hidden');
        clearElementMessage('reviewFormMessage');
    },

    async saveReview(moduleCode) {
        const rating = Number(document.getElementById('reviewRating').value);
        const comment = document.getElementById('reviewComment').value.trim();
        const button = document.getElementById('submitReviewBtn');
        const isEditing = this.editingReviewId !== null;
        const endpoint = isEditing ? `/api/reviews/${this.editingReviewId}` : '/api/reviews';
        const payload = { rating, comment };
        if (!isEditing) payload.module_code = moduleCode;

        button.disabled = true;
        button.textContent = isEditing ? 'Saving...' : 'Submitting...';
        clearElementMessage('reviewFormMessage');

        try {
            const response = await fetch(endpoint, {
                method: isEditing ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok) {
                showFormMessage(result.error || 'Could not save review.', 'danger');
                return;
            }
            this.resetReviewForm();
            await this.refreshReviewViews(moduleCode);
            showFormMessage(isEditing ? 'Review updated.' : 'Review submitted.', 'success');
        } catch (error) {
            console.error('Error saving review:', error);
            showFormMessage('Could not save review. Please try again.', 'danger');
        } finally {
            button.disabled = false;
            button.textContent = this.editingReviewId === null ? 'Submit Review' : 'Save Changes';
        }
    },

    async deleteReview(reviewId) {
        if (!window.confirm('Delete this review permanently?')) return;
        try {
            const response = await fetch(`/api/reviews/${reviewId}`, { method: 'DELETE' });
            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Could not delete review.');
            }
            if (this.editingReviewId === reviewId) this.resetReviewForm();
            await this.refreshReviewViews(this.currentModuleCode);
            showFormMessage('Review deleted.', 'success');
        } catch (error) {
            console.error('Error deleting review:', error);
            showFormMessage(error.message, 'danger');
        }
    },

    async refreshReviewViews(moduleCode) {
        await this.loadReviews(moduleCode);
        await DataManager.refreshRatingSummaries();
        UIRenderer.updateRatingDisplay(moduleCode);
    }
};

function showFormMessage(message, type) {
    const el = document.getElementById('reviewFormMessage');
    if (el) showMessage(el, message, type);
}

function clearElementMessage(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = '';
        el.className = 'hidden mb-3 rounded-lg px-4 py-2.5 text-sm';
    }
}

function formatTimestamp(value) {
    const date = parseTimestamp(value);
    return date ? formatReviewDate(date) : escapeHtml(value);
}

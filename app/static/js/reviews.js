/**
 * Powers the all-module review dashboard.
 * @module reviews
 */
const ReviewDashboard = {
    reviews: [],
    editingReviewId: null,
    elements: {},
    modal: null,

    async init() {
        this.cacheElements();
        this.bindEvents();
        this.modal = createModalController({
            overlayId: 'editReviewModalOverlay',
            closeBtnId: 'editReviewModalClose',
            cancelBtnId: 'editReviewCancelBtn'
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

    cacheElements() {
        this.elements = {
            list: document.getElementById('reviewDashboardList'),
            search: document.getElementById('reviewSearch'),
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
            saveButton: document.getElementById('saveDashboardReviewBtn')
        };
    },

    bindEvents() {
        this.elements.search.addEventListener('input', () => this.renderReviews());
        this.elements.ratingFilter.addEventListener('change', () => this.renderReviews());
        this.elements.sort.addEventListener('change', () => this.renderReviews());
        this.elements.saveButton.addEventListener('click', () => this.saveEdit());
    },

    async loadReviews() {
        const response = await fetch('/api/reviews');
        if (!response.ok) throw new Error('Failed to load reviews.');
        this.reviews = await response.json();
    },

    render() {
        this.renderStats();
        this.renderReviews();
    },

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

    getFilteredReviews() {
        const query = this.elements.search.value.trim().toLowerCase();
        const rating = this.elements.ratingFilter.value;

        const filtered = this.reviews.filter(review => {
            const module = DataManager.getModule(review.module_code);
            const searchable = [review.module_code, module ? module.name : '', review.comment].join(' ').toLowerCase();
            const matchesQuery = !query || searchable.includes(query);
            const matchesRating = rating === 'all' || review.rating === Number(rating);
            return matchesQuery && matchesRating;
        });

        const dir = this.elements.sort.value === 'oldest' ? 1 : -1;
        return filtered.sort((a, b) => {
            const aTime = parseTimestamp(a.created_at)?.getTime() || 0;
            const bTime = parseTimestamp(b.created_at)?.getTime() || 0;
            return (aTime - bTime) * dir;
        });
    },

    renderReviews() {
        const filtered = this.getFilteredReviews();
        const label = filtered.length === 1 ? 'review' : 'reviews';
        this.elements.resultCount.textContent = `${filtered.length} ${label}`;
        this.elements.list.innerHTML = '';

        if (filtered.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'py-16 text-center';
            empty.innerHTML = `
                <div class="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-800 mb-4">
                    <i data-lucide="message-square" class="w-8 h-8 text-slate-400 dark:text-slate-400"></i>
                </div>
                <h3 class="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-1">No reviews found</h3>
                <p class="text-sm text-slate-500 dark:text-slate-400">Try a different search or rating filter.</p>
            `;
            this.elements.list.appendChild(empty);
            lucide.createIcons();
            return;
        }

        filtered.forEach(r => this.elements.list.appendChild(this.createReviewCard(r)));
        lucide.createIcons();
    },

    createReviewCard(review) {
        const module = DataManager.getModule(review.module_code);
        const article = document.createElement('article');
        article.className = 'glass-card p-5';
        article.innerHTML = `
            <div class="flex items-start justify-between gap-3 mb-3">
                <div>
                    <span class="text-xs font-bold uppercase tracking-wider text-primary-500 dark:text-primary-400">${review.module_code}</span>
                    <h3 class="text-base font-bold text-slate-900 dark:text-white mb-1">${module ? module.name : 'Module name unavailable'}</h3>
                    <div class="star-rating flex gap-0.5 text-sm" aria-label="${review.rating} out of 5 stars">
                        ${createStars(review.rating)}
                    </div>
                </div>
                ${createReviewActionsHTML(review.id)}
            </div>
            <div class="rounded-lg bg-slate-50 dark:bg-slate-800/60 border-l-[3px] border-l-primary-300 dark:border-l-primary-500 pl-3 py-2 mb-3">
                <p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">${review.comment || 'No written comment'}</p>
            </div>
            <small class="text-xs text-slate-400 dark:text-slate-400">${this.formatDate(review)}</small>
        `;

        if (!review.comment) {
            article.querySelector('.text-sm.text-slate-700').classList.add('text-slate-400', 'dark:text-slate-400', 'italic');
        }
        article.querySelector('.edit-review-btn').addEventListener('click', () => this.openEdit(review.id));
        article.querySelector('.delete-review-btn').addEventListener('click', () => this.deleteReview(review.id));
        return article;
    },

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

    async saveEdit() {
        if (this.editingReviewId === null) return;
        this.elements.saveButton.disabled = true;
        this.elements.saveButton.textContent = 'Saving...';

        try {
            const response = await fetch(`/api/reviews/${this.editingReviewId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    rating: Number(this.elements.editRating.value),
                    comment: this.elements.editComment.value.trim()
                })
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

    async deleteReview(reviewId) {
        if (!window.confirm('Delete this review permanently?')) return;
        try {
            const response = await fetch(`/api/reviews/${reviewId}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Could not delete review.');
            await this.refresh();
            showMessage(this.elements.message, 'Review deleted.', 'success');
        } catch (error) {
            console.error('Could not delete review:', error);
            showMessage(this.elements.message, error.message, 'danger');
        }
    },

    async refresh() {
        await Promise.all([this.loadReviews(), DataManager.refreshRatingSummaries()]);
        this.render();
    },

    showEditMessage(message) {
        showMessage(this.elements.editMessage, message, 'danger');
    },

    clearEditMessage() {
        this.elements.editMessage.textContent = '';
        this.elements.editMessage.className = 'hidden mb-4 rounded-lg px-4 py-2.5 text-sm';
    },

    formatDate(review) {
        const value = review.updated_at || review.created_at;
        if (!value) return '';
        const date = parseTimestamp(value);
        const prefix = review.updated_at ? 'Updated ' : 'Submitted ';
        return prefix + (date ? formatReviewDate(date) : value);
    }
};

document.addEventListener('DOMContentLoaded', () => ReviewDashboard.init());

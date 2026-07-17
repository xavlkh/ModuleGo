// Powers the all-module review dashboard.
const ReviewDashboard = {
    reviews: [],
    editingReviewId: null,
    editModal: null,
    elements: {},

    async init() {
        this.cacheElements();
        this.bindEvents();
        this.editModal = new bootstrap.Modal(document.getElementById('editReviewModal'));

        try {
            await Promise.all([DataManager.loadData(), this.loadReviews()]);
            this.render();
        } catch (error) {
            console.error('Could not initialize review dashboard:', error);
            this.elements.list.innerHTML = '<p class="text-danger">Could not load the review dashboard.</p>';
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
        const modulesRated = new Set(this.reviews.map(review => review.module_code)).size;
        const now = new Date();
        const monthlyReviewCount = this.reviews.filter(review => {
            const submittedAt = this.getSubmittedDate(review);
            return submittedAt
                && submittedAt.getFullYear() === now.getFullYear()
                && submittedAt.getMonth() === now.getMonth();
        }).length;

        this.elements.reviewCount.textContent = String(count);
        this.elements.monthlyReviewCount.textContent = String(monthlyReviewCount);
        this.elements.moduleCount.textContent = String(modulesRated);
    },

    getFilteredReviews() {
        const query = this.elements.search.value.trim().toLowerCase();
        const rating = this.elements.ratingFilter.value;

        const filtered = this.reviews.filter(review => {
            const module = DataManager.getModule(review.module_code);
            const searchable = [
                review.module_code,
                module ? module.name : '',
                review.comment
            ].join(' ').toLowerCase();
            const matchesQuery = !query || searchable.includes(query);
            const matchesRating = rating === 'all' || review.rating === Number(rating);
            return matchesQuery && matchesRating;
        });

        const direction = this.elements.sort.value === 'oldest' ? 1 : -1;
        return filtered.sort((first, second) => {
            const firstDate = this.getSubmittedDate(first);
            const secondDate = this.getSubmittedDate(second);
            const firstTime = firstDate ? firstDate.getTime() : 0;
            const secondTime = secondDate ? secondDate.getTime() : 0;
            return (firstTime - secondTime) * direction;
        });
    },

    renderReviews() {
        const filtered = this.getFilteredReviews();
        const label = filtered.length === 1 ? 'review' : 'reviews';
        this.elements.resultCount.textContent = `${filtered.length} ${label}`;
        this.elements.list.innerHTML = '';

        if (filtered.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'review-dashboard-empty';
            empty.innerHTML = '<i class="bi bi-chat-square-text"></i><h3 class="h5 mt-3">No reviews found</h3><p class="text-muted mb-0">Try a different search or rating filter.</p>';
            this.elements.list.appendChild(empty);
            return;
        }

        filtered.forEach(review => this.elements.list.appendChild(this.createReviewCard(review)));
    },

    createReviewCard(review) {
        const module = DataManager.getModule(review.module_code);
        const article = document.createElement('article');
        article.className = 'dashboard-review-card';
        article.innerHTML = `
            <div class="dashboard-review-heading">
                <div>
                    <span class="dashboard-review-code"></span>
                    <h3 class="h5 mb-1 dashboard-review-name"></h3>
                    <div class="review-stars" aria-label="${review.rating} out of 5 stars">
                        ${this.createStars(review.rating)}
                    </div>
                </div>
                <div class="review-actions">
                    <button class="btn btn-sm btn-outline-primary dashboard-edit-btn" type="button" aria-label="Edit review"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-sm btn-outline-danger dashboard-delete-btn" type="button" aria-label="Delete review"><i class="bi bi-trash"></i></button>
                </div>
            </div>
            <p class="dashboard-review-comment"></p>
            <small class="text-muted dashboard-review-date"></small>
        `;

        article.querySelector('.dashboard-review-code').textContent = review.module_code;
        article.querySelector('.dashboard-review-name').textContent = module ? module.name : 'Module name unavailable';
        const commentElement = article.querySelector('.dashboard-review-comment');
        commentElement.textContent = review.comment || 'No written comment';
        if (!review.comment) commentElement.classList.add('text-muted', 'fst-italic');
        article.querySelector('.dashboard-review-date').textContent = this.formatDate(review);
        article.querySelector('.dashboard-edit-btn').addEventListener('click', () => this.openEdit(review.id));
        article.querySelector('.dashboard-delete-btn').addEventListener('click', () => this.deleteReview(review.id));
        return article;
    },

    openEdit(reviewId) {
        const review = this.reviews.find(item => item.id === reviewId);
        if (!review) return;
        const module = DataManager.getModule(review.module_code);

        this.editingReviewId = reviewId;
        this.elements.editModule.textContent = `${review.module_code} - ${module ? module.name : 'Module'}`;
        this.elements.editRating.value = String(review.rating);
        this.elements.editComment.value = review.comment;
        this.clearEditMessage();
        this.editModal.show();
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
            this.editModal.hide();
            this.showMessage('Review updated.', 'success');
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
            this.showMessage('Review deleted.', 'success');
        } catch (error) {
            console.error('Could not delete review:', error);
            this.showMessage(error.message, 'danger');
        }
    },

    async refresh() {
        await Promise.all([this.loadReviews(), DataManager.refreshRatingSummaries()]);
        this.render();
    },

    showMessage(message, type) {
        this.elements.message.textContent = message;
        this.elements.message.className = `alert alert-${type}`;
    },

    showEditMessage(message) {
        this.elements.editMessage.textContent = message;
        this.elements.editMessage.className = 'alert alert-danger py-2';
    },

    clearEditMessage() {
        this.elements.editMessage.textContent = '';
        this.elements.editMessage.className = 'alert d-none py-2';
    },

    createStars(rating) {
        return '<i class="bi bi-star-fill"></i>'.repeat(rating)
            + '<i class="bi bi-star"></i>'.repeat(5 - rating);
    },

    getSubmittedDate(review) {
        if (!review.created_at) return null;
        const value = review.created_at;
        const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`;
        const date = new Date(normalized);
        return Number.isNaN(date.getTime()) ? null : date;
    },

    formatDate(review) {
        const value = review.updated_at || review.created_at;
        if (!value) return '';
        const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`;
        const date = new Date(normalized);
        const prefix = review.updated_at ? 'Updated ' : 'Submitted ';
        return prefix + (Number.isNaN(date.getTime()) ? value : date.toLocaleString());
    }
};

document.addEventListener('DOMContentLoaded', () => ReviewDashboard.init());

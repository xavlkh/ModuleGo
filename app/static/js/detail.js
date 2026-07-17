// Shows module details and manages the complete review lifecycle.
const DetailManager = {
    modal: null,
    currentModuleCode: null,
    currentReviews: new Map(),
    editingReviewId: null,

    init() {
        this.modal = new bootstrap.Modal(document.getElementById('moduleModal'));
    },

    showModuleDetail(moduleCode) {
        const module = DataManager.getModule(moduleCode);
        if (!module) return;

        this.currentModuleCode = module.code;
        this.editingReviewId = null;

        const modalBody = document.getElementById('moduleModalBody');
        const modalTitle = document.getElementById('moduleModalLabel');
        modalTitle.textContent = `${module.code} - ${module.name}`;
        modalBody.innerHTML = this.createDetailContent(module);

        document.getElementById('submitReviewBtn').addEventListener('click', () => {
            this.saveReview(module.code);
        });
        document.getElementById('cancelEditReviewBtn').addEventListener('click', () => {
            this.resetReviewForm();
        });

        this.modal.show();
        this.loadReviews(module.code);
    },

    createDetailContent(module) {
        const diplomas = DataManager.getDiplomasByModule(module.code);
        const diplomasHTML = diplomas.length > 0
            ? diplomas.map(diploma => `
                <li class="list-group-item">
                    <div class="fw-bold">${this.escapeHtml(diploma.name)}</div>
                    <small class="text-muted">
                        ${this.escapeHtml(diploma.id)} &bull; ${this.escapeHtml(diploma.school)}
                    </small>
                </li>
            `).join('')
            : `
                <li class="list-group-item text-muted">
                    No diploma information available for this module.
                </li>
            `;

        return `
            <div class="module-detail-header">
                <div class="module-code">${this.escapeHtml(module.code)}</div>
                <div class="module-name">${this.escapeHtml(module.name)}</div>
                <div class="mt-2">
                    <span class="badge bg-secondary">${this.escapeHtml(module.school || 'School not listed')}</span>
                </div>
            </div>

            <div class="mb-4">
                <h6 class="fw-bold mb-2">Description</h6>
                <p class="text-muted">${this.escapeHtml(module.description)}</p>
            </div>

            <div class="mb-4">
                <h6 class="fw-bold mb-2">Diplomas taking this module</h6>
                <ul class="list-group">${diplomasHTML}</ul>
            </div>

            <div class="mt-4 mb-4">
                <a href="${this.escapeHtml(module.url || '#')}" target="_blank" rel="noopener" class="btn btn-outline-primary">
                    <i class="bi bi-box-arrow-up-right me-2"></i>View on RP Website
                </a>
            </div>

            <hr>

            <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <h6 class="fw-bold mb-0">Student Reviews</h6>
                <div id="reviewSummary" class="review-summary">Loading rating...</div>
            </div>

            <div id="reviewsList" class="mb-4" aria-live="polite">
                <div class="d-flex align-items-center gap-2 text-muted small">
                    <span class="spinner-border spinner-border-sm" role="status"></span>
                    Loading reviews...
                </div>
            </div>

            <div id="reviewFormCard" class="card card-body bg-light">
                <h6 id="reviewFormTitle" class="fw-bold mb-3">Leave a Review</h6>
                <div id="reviewFormMessage" class="alert d-none py-2" role="alert"></div>
                <div class="mb-2">
                    <label for="reviewRating" class="form-label">Rating</label>
                    <select id="reviewRating" class="form-select form-select-sm">
                        <option value="5">5 - Excellent</option>
                        <option value="4">4 - Good</option>
                        <option value="3">3 - Average</option>
                        <option value="2">2 - Poor</option>
                        <option value="1">1 - Terrible</option>
                    </select>
                </div>
                <div class="mb-2">
                    <label for="reviewComment" class="form-label">Comment</label>
                    <textarea id="reviewComment" class="form-control form-control-sm" rows="3" maxlength="500" placeholder="What did you think of this module?"></textarea>
                    <div class="form-text">Optional, maximum 500 characters.</div>
                </div>
                <div class="d-flex gap-2">
                    <button id="submitReviewBtn" class="btn btn-sm btn-primary" type="button">Submit Review</button>
                    <button id="cancelEditReviewBtn" class="btn btn-sm btn-outline-secondary d-none" type="button">Cancel edit</button>
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
            this.currentReviews = new Map(reviews.map(review => [review.id, review]));
            this.renderReviewSummary(reviews);

            if (reviews.length === 0) {
                reviewsList.innerHTML = '<p class="text-muted small">No reviews yet. Be the first!</p>';
                return;
            }

            reviewsList.innerHTML = reviews.map(review => this.createReviewMarkup(review)).join('');
            reviewsList.querySelectorAll('.edit-review-btn').forEach(button => {
                button.addEventListener('click', () => {
                    this.startEditReview(Number(button.dataset.reviewId));
                });
            });
            reviewsList.querySelectorAll('.delete-review-btn').forEach(button => {
                button.addEventListener('click', () => {
                    this.deleteReview(Number(button.dataset.reviewId));
                });
            });
        } catch (error) {
            console.error('Error loading reviews:', error);
            reviewsList.innerHTML = '<p class="text-danger small">Could not load reviews.</p>';
            this.renderReviewSummary([]);
        }
    },

    createReviewMarkup(review) {
        const comment = review.comment
            ? this.escapeHtml(review.comment)
            : '<span class="text-muted fst-italic">No written comment</span>';
        const updated = review.updated_at
            ? `<span class="ms-2">Edited ${this.formatDate(review.updated_at)}</span>`
            : '';

        return `
            <article class="review-item" data-review-id="${review.id}">
                <div class="d-flex justify-content-between gap-3">
                    <div>
                        <div class="review-stars" aria-label="${review.rating} out of 5 stars">
                            ${this.createStars(review.rating)}
                        </div>
                        <p class="mb-1 small review-comment">${comment}</p>
                        <small class="text-muted review-created_at">
                            ${this.formatDate(review.created_at)}${updated}
                        </small>
                    </div>
                    <div class="review-actions">
                        <button class="btn btn-sm btn-outline-primary edit-review-btn" type="button" data-review-id="${review.id}" aria-label="Edit review">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger delete-review-btn" type="button" data-review-id="${review.id}" aria-label="Delete review">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </article>
        `;
    },

    renderReviewSummary(reviews) {
        const summary = document.getElementById('reviewSummary');
        if (!summary) return;

        if (reviews.length === 0) {
            summary.innerHTML = '<i class="bi bi-star me-1"></i>No ratings yet';
            return;
        }

        const average = reviews.reduce((total, review) => total + review.rating, 0) / reviews.length;
        const label = reviews.length === 1 ? 'review' : 'reviews';
        summary.innerHTML = `
            <i class="bi bi-star-fill me-1"></i>
            <strong>${average.toFixed(1)}</strong> (${reviews.length} ${label})
        `;
    },

    startEditReview(reviewId) {
        const review = this.currentReviews.get(reviewId);
        if (!review) return;

        this.editingReviewId = reviewId;
        document.getElementById('reviewFormTitle').textContent = 'Edit Review';
        document.getElementById('reviewRating').value = String(review.rating);
        document.getElementById('reviewComment').value = review.comment;
        document.getElementById('submitReviewBtn').textContent = 'Save Changes';
        document.getElementById('cancelEditReviewBtn').classList.remove('d-none');
        this.clearFormMessage();
        document.getElementById('reviewFormCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    resetReviewForm() {
        this.editingReviewId = null;
        document.getElementById('reviewFormTitle').textContent = 'Leave a Review';
        document.getElementById('reviewRating').value = '5';
        document.getElementById('reviewComment').value = '';
        document.getElementById('submitReviewBtn').textContent = 'Submit Review';
        document.getElementById('cancelEditReviewBtn').classList.add('d-none');
        this.clearFormMessage();
    },

    async saveReview(moduleCode) {
        const rating = Number(document.getElementById('reviewRating').value);
        const comment = document.getElementById('reviewComment').value.trim();
        const button = document.getElementById('submitReviewBtn');
        const isEditing = this.editingReviewId !== null;
        const endpoint = isEditing ? `/api/reviews/${this.editingReviewId}` : '/api/reviews';
        const method = isEditing ? 'PUT' : 'POST';
        const payload = { rating, comment };
        if (!isEditing) payload.module_code = moduleCode;

        button.disabled = true;
        button.textContent = isEditing ? 'Saving...' : 'Submitting...';
        this.clearFormMessage();

        try {
            const response = await fetch(endpoint, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();

            if (!response.ok) {
                this.showFormMessage(result.error || 'Could not save review.', 'danger');
                return;
            }

            this.resetReviewForm();
            await this.refreshReviewViews(moduleCode);
            this.showFormMessage(isEditing ? 'Review updated.' : 'Review submitted.', 'success');
        } catch (error) {
            console.error('Error saving review:', error);
            this.showFormMessage('Could not save review. Please try again.', 'danger');
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
            this.showFormMessage('Review deleted.', 'success');
        } catch (error) {
            console.error('Error deleting review:', error);
            this.showFormMessage(error.message, 'danger');
        }
    },

    async refreshReviewViews(moduleCode) {
        await this.loadReviews(moduleCode);
        await DataManager.refreshRatingSummaries();
        UIRenderer.updateRatingDisplay(moduleCode);
    },

    showFormMessage(message, type) {
        const element = document.getElementById('reviewFormMessage');
        if (!element) return;
        element.textContent = message;
        element.className = `alert alert-${type} py-2`;
    },

    clearFormMessage() {
        const element = document.getElementById('reviewFormMessage');
        if (!element) return;
        element.textContent = '';
        element.className = 'alert d-none py-2';
    },

    createStars(rating) {
        const filled = '<i class="bi bi-star-fill"></i>'.repeat(rating);
        const empty = '<i class="bi bi-star"></i>'.repeat(5 - rating);
        return filled + empty;
    },

    formatDate(value) {
        if (!value) return '';
        const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`;
        const date = new Date(normalized);
        return Number.isNaN(date.getTime()) ? this.escapeHtml(value) : date.toLocaleString();
    },

    escapeHtml(value) {
        return String(value || '').replace(/[&<>'"]/g, character => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        })[character]);
    }
};

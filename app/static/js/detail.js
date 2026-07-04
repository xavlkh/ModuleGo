// Shows full information for a selected module.
const DetailManager = {
    modal: null,
    currentModuleCode: null,

    init() {
        // Prepare the Bootstrap modal instance.
        this.modal = new bootstrap.Modal(document.getElementById('moduleModal'));
    },

    showModuleDetail(moduleCode) {
        // Find the selected module before rendering details.
        const module = DataManager.getModule(moduleCode);
        if (!module) return;

        this.currentModuleCode = moduleCode;
        const modalBody = document.getElementById('moduleModalBody');
        const modalTitle = document.getElementById('moduleModalLabel');
        
        modalTitle.textContent = `${module.code} - ${module.name}`;

        // Inject the layout and our new review system
        modalBody.innerHTML = this.createDetailContent(module);

        this.modal.show();

        // Fetch existing reviews from the Python Backend
        this.loadReviews(moduleCode);

        // Listen for the user clicking the "Submit Review" button
        document.getElementById('submitReviewBtn').addEventListener('click', () => {
            this.submitReview(moduleCode);
        });
    },

    createDetailContent(module) {
        // Get all diplomas that include this module code
        const diplomas = DataManager.getDiplomasByModule(module.code);

        // Convert diploma list into HTML
        const diplomasHTML = diplomas.length > 0
            ? diplomas.map(diploma => `
                <li class="list-group-item">
                    <div class="fw-bold">${diploma.name}</div>
                    <small class="text-muted">${diploma.id} • ${diploma.school}</small>
                </li>
            `).join('')
            : `
                <li class="list-group-item text-muted">
                    No diploma information available for this module.
                </li>
            `;

        return `
            <div class="module-detail-header">
                <div class="module-code">${module.code}</div>
                <div class="module-name">${module.name}</div>
                <div class="mt-2">
                    <span class="badge bg-secondary">${module.school}</span>
                </div>
            </div>

            <div class="mb-4">
                <h6 class="fw-bold mb-2">Description</h6>
                <p class="text-muted">${module.description}</p>
            </div>

            <!-- Display diplomas associated with this module -->
            <div class="mb-4">
                <h6 class="fw-bold mb-2">Diplomas taking this module</h6>
                <ul class="list-group">
                    ${diplomasHTML}
                </ul>
            </div>

            <div class="mt-4 mb-4">
                <a href="${module.url}" target="_blank" class="btn btn-outline-primary">
                    <i class="bi bi-box-arrow-up-right me-2"></i>View on RP Website
                </a>
            </div>

            <hr>

            <h6 class="fw-bold mb-3">Student Reviews</h6>

            <div id="reviewsList" class="mb-4">
                <div class="text-center text-muted spinner-border spinner-border-sm" role="status"></div> Loading reviews...
            </div>

            <div class="card card-body bg-light">
                <h7 class="fw-bold mb-2">Leave a Review</h7>
                <div class="mb-2">
                    <label class="form-label">Rating</label>
                    <select id="reviewRating" class="form-select form-select-sm">
                        <option value="5">5 - Excellent</option>
                        <option value="4">4 - Good</option>
                        <option value="3">3 - Average</option>
                        <option value="2">2 - Poor</option>
                        <option value="1">1 - Terrible</option>
                    </select>
                </div>
                <div class="mb-2">
                    <label class="form-label">Comment</label>
                    <textarea id="reviewComment" class="form-control form-control-sm" rows="2" placeholder="What did you think of this module?"></textarea>
                </div>
                <button id="submitReviewBtn" class="btn btn-sm btn-primary">Submit Review</button>
            </div>
        `;
    },

    // READ: GET request to your Flask API
    async loadReviews(moduleCode) {
        const reviewsList = document.getElementById('reviewsList');
        try {
            const response = await fetch(`/api/reviews/${moduleCode}`);
            if (!response.ok) throw new Error('Failed to fetch');
            const reviews = await response.json();

            if (reviews.length === 0) {
                reviewsList.innerHTML = '<p class="text-muted small">No reviews yet. Be the first!</p>';
                return;
            }

            let html = '';
            reviews.forEach(r => {
                html += `
                    <div class="border-bottom pb-2 mb-2">
                        <div class="text-warning mb-1">
                            ${'★'.repeat(r.RATING)}${'☆'.repeat(5 - r.RATING)}
                        </div>
                        <p class="mb-1 small">${r.COMMENT}</p>
                        <small class="text-muted" style="font-size: 0.7em;">${new Date(r.TIMESTAMP).toLocaleString()}</small>
                    </div>
                `;
            });
            reviewsList.innerHTML = html;
        } catch (error) {
            reviewsList.innerHTML = '<p class="text-danger small">Could not load reviews.</p>';
        }
    },

    // CREATE: POST request to your Flask API
    async submitReview(moduleCode) {
        const rating = document.getElementById('reviewRating').value;
        const comment = document.getElementById('reviewComment').value;
        const btn = document.getElementById('submitReviewBtn');

        btn.disabled = true;
        btn.textContent = "Submitting...";

        try {
            const response = await fetch('/api/reviews', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    module_code: moduleCode,
                    rating: parseInt(rating),
                    comment: comment
                })
            });

            if (response.ok) {
                document.getElementById('reviewComment').value = '';
                await this.loadReviews(moduleCode); // Refresh the list
            }
        } catch (error) {
            console.error("Error posting review:", error);
            alert("Failed to submit review. Is your Python server running?");
        } finally {
            btn.disabled = false;
            btn.textContent = "Submit Review";
        }
    }
};

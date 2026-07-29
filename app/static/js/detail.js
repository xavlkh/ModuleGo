/**
 * Module detail modal: shows full module info, diploma list, and manages
 * the review lifecycle (read / create / edit / delete) within the modal.
 * @module detail
 */
const DetailManager = {
    /** @type {string|null} Module code currently shown in the modal. */
    currentModuleCode: null,
    /** @type {Map<number, Object>} Reviews for the current module, keyed by ID. */
    currentReviews: new Map(),
    /** @type {number|null} ID of the review being edited, or null for create mode. */
    editingReviewId: null,
    /** @type {{show: Function, hide: Function, init: Function}|null} Modal controller. */
    modal: null,

    /**
     * Initialise the modal controller for the module detail overlay.
     */
    init() {
        this.modal = createModalController({
            overlayId: 'moduleModalOverlay',
            closeBtnId: 'moduleModalClose',
        });
        this.modal.init();
    },

    /** Show the module detail modal. */
    showModal() { this.modal.show(); },

    /** Hide the module detail modal. */
    hideModal() { this.modal.hide(); },

    /**
     * Open the detail modal for a module, populate its content, and
     * kick off an async review load.
     * @param {string} moduleCode - The module code to display.
     */
    showModuleDetail(moduleCode) {
        const module = DataManager.getModule(moduleCode);
        if (!module) return;

        this.currentModuleCode = module.code;
        this.editingReviewId = null;

        document.getElementById('moduleModalLabel').textContent = `${module.code} - ${module.name}`;
        document.getElementById('moduleModalBody').innerHTML = this.createDetailContent(module);
        // Set up bookmark button event listener
        const bookmarkBtn =
        document.getElementById('bookmarkModuleBtn');

        if (bookmarkBtn) {
            bookmarkBtn.addEventListener('click', async () => {
                const bookmarked = await BookmarkManager.toggle(module.code);

                bookmarkBtn.innerHTML = `
                    <i
                        data-lucide="bookmark"
                        class="w-5 h-5 ${
                            bookmarked
                                ? 'fill-primary-500 text-primary-500'
                                : 'text-zinc-400 dark:text-zinc-500'
                        }"
                    ></i>
                `;

                bookmarkBtn.setAttribute(
                    'aria-label',
                    bookmarked
                        ? 'Remove bookmark'
                        : 'Add bookmark'
               );

                bookmarkBtn.title =
                    bookmarked
                        ? 'Remove bookmark'
                        : 'Add bookmark';

                lucide.createIcons();
           });
        }

        document.getElementById('submitReviewBtn').addEventListener('click', () => this.saveReview(module.code));
        document.getElementById('cancelEditReviewBtn').addEventListener('click', () => this.resetReviewForm());

        this.showModal();
        this.refreshReviewViews(module.code);
        lucide.createIcons();
        this.initCollapsibles();

        const diplomasToggle = document.querySelector('[data-toggle="diplomas"]');
        if (diplomasToggle) {
            diplomasToggle.addEventListener('click', () => {
                const expanded = diplomasToggle.dataset.expanded === 'true';
                diplomasToggle.dataset.expanded = (!expanded).toString();
                const icon = diplomasToggle.querySelector('i');
                const label = diplomasToggle.querySelector('span');
                const items = document.querySelectorAll('#diplomasList > li');
                if (!expanded) {
                    items.forEach(item => item.classList.remove('collapsible-hidden'));
                    label.textContent = 'Show fewer';
                    icon.classList.add('rotate-180');
                } else {
                    items.forEach((item, i) => {
                        if (i >= 3) item.classList.add('collapsible-hidden');
                    });
                    label.textContent = `Show all ${items.length} diplomas`;
                    icon.classList.remove('rotate-180');
                }
            });
        }
    },

    /**
     * Build the HTML for the module detail body (header, synopsis, source
     * link, diploma list, reviews section, and review form).
     * @param {Object} module - The module data object.
     * @returns {string} Inner HTML string for the modal body.
     */
    createDetailContent(module) {
        const rawDiplomas = DataManager.getDiplomasByModule(module.code);
        const minors = DataManager.getMinorsByModule(module.code);
        const isBookmarked = BookmarkManager.isBookmarked(module.code);

        // Merge same diploma + category, collecting all major names
        const merged = new Map();
        for (const d of rawDiplomas) {
            const key = `${d.course_code}||${d.category}`;
            if (merged.has(key)) {
                const existing = merged.get(key);
                if (d.major_name && !existing.majorNames.includes(d.major_name)) {
                    existing.majorNames.push(d.major_name);
                }
            } else {
                merged.set(key, {
                    ...d,
                    majorNames: d.major_name ? [d.major_name] : [],
                });
            }
        }
        const diplomas = [...merged.values()];

        const diplomasHTML = diplomas.length > 0
            ? diplomas.map(d => {
                const catColors = {
                    'General': 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
                    'Major': 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
                    'Discipline': 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
                    'Elective': 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
                    'Industry': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
                };
                const catClass = catColors[d.category] || 'bg-zinc-100 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300';
                const diplomaUrl = d.url ? escapeHtml(d.url) : '#';
                const targetAttr = d.url ? 'target="_blank" rel="noopener"' : '';
                const majorLabel = d.category === 'Major' && d.majorNames && d.majorNames.length > 0
                    ? `<div class="flex flex-col gap-0.5">${d.majorNames.map(name => `<span class="text-xs text-indigo-500 dark:text-indigo-400 font-medium">${escapeHtml(name)}</span>`).join('')}</div>`
                    : '';
                return `
                <li>
                    <a href="${diplomaUrl}" ${targetAttr} class="flex flex-col gap-1 rounded-lg border border-zinc-100 dark:border-zinc-700 px-4 py-3 bg-white/60 dark:bg-zinc-800/60 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-700/60">
                        <div class="flex items-center justify-between gap-2">
                            <div class="font-semibold text-zinc-900 dark:text-white">${escapeHtml(d.course_name || '')}</div>
                            <span class="flex-shrink-0 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${catClass}">${escapeHtml(d.category)}</span>
                        </div>
                        ${majorLabel}
                        <div class="text-xs text-zinc-500 dark:text-zinc-400">${escapeHtml(d.course_code || '')} &bull; ${escapeHtml(d.school_name || d.school_abbr || '')}</div>
                    </a>
                </li>`;
            }).join('')
            : '<li class="rounded-lg border border-dashed border-zinc-200 dark:border-zinc-700 px-4 py-6 text-center text-zinc-400 dark:text-zinc-400 text-sm">No diploma information available for this module.</li>';

        const minorsHTML = minors.length > 0
            ? minors.map(m => {
                const typeColors = {
                    'Broad-Based': 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
                    'Discipline-Related': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300',
                };
                const typeClass = typeColors[m.minor_type] || 'bg-zinc-100 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300';
                const minorUrl = m.url ? escapeHtml(m.url) : '#';
                const targetAttr = m.url ? 'target="_blank" rel="noopener"' : '';
                const moduleCount = (m.modules || []).length;
                return `
                <li>
                    <a href="${minorUrl}" ${targetAttr} class="flex flex-col gap-1 rounded-lg border border-zinc-100 dark:border-zinc-700 px-4 py-3 bg-white/60 dark:bg-zinc-800/60 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-700/60">
                        <div class="flex items-center justify-between gap-2">
                            <div class="font-semibold text-zinc-900 dark:text-white">${escapeHtml(m.minor_name || '')}</div>
                            <span class="flex-shrink-0 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${typeClass}">${escapeHtml(m.minor_type || '')}</span>
                        </div>
                        <div class="text-xs text-zinc-500 dark:text-zinc-400">${moduleCount} modules</div>
                    </a>
                </li>`;
            }).join('')
            : '<li class="rounded-lg border border-dashed border-zinc-200 dark:border-zinc-700 px-4 py-6 text-center text-zinc-400 dark:text-zinc-400 text-sm">Not part of any minor programme.</li>';

        return `
            <div class="module-header rounded-xl p-6 mb-6">
                <div class="flex items-start justify-between gap-4">
                    <div class="min-w-0">
                        <div class="text-xs font-bold uppercase tracking-wider text-primary-500 dark:text-primary-400 mb-1">${escapeHtml(module.code)}</div>
                        <div class="text-xl font-bold text-zinc-900 dark:text-white mb-2">${escapeHtml(module.name)}</div>
                        <div class="text-sm font-medium text-primary-700 dark:text-primary-300">${escapeHtml(module.school || 'School not listed')}</div>
                    </div>
                    <button 
                        id="bookmarkModuleBtn"
                        type="button"
                        data-module-code="${escapeHtml(module.code)}"
                        class="flex-shrink-0 inline-flex items-center justify-center w-11 h-11 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white/70 dark:bg-zinc-800/70 text-zinc-400 dark:text-zinc-500 hover:text-primary-600 hover:border-primary-300 dark:hover:text-primary-400 dark:hover:border-primary-600 transition-all"
                        aria-label="${isBookmarked ? 'Remove bookmark' : 'Add bookmark'}"
                        title="${isBookmarked ? 'Remove bookmark' : 'Add bookmark'}"
                   >
                        <i
                            data-lucide="bookmark"
                            class="w-5 h-5 ${
                                isBookmarked
                                ? 'fill-primary-500 text-primary-500'
                                : 'text-zinc-400 dark:text-zinc-500'
                        }"
                        ></i>
                    </button>
                </div>
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
                <h6 class="text-sm font-bold text-slate-900 dark:text-white mb-2">Diplomas offering this module (${diplomas.length})</h6>
                <ul id="diplomasList" class="grid gap-2">${diplomasHTML}</ul>
                ${diplomas.length > 3 ? `
                <button class="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors" data-toggle="diplomas" data-expanded="false">
                    <span>Show all ${diplomas.length} diplomas</span>
                    <i data-lucide="chevron-down" class="w-3.5 h-3.5 transition-transform duration-200"></i>
                </button>
                ` : ''}
            </div>
            <div class="mb-6">
                <h6 class="text-sm font-bold text-slate-900 dark:text-white mb-2">Minor programmes offering this module (${minors.length})</h6>
                <ul id="minorsList" class="grid gap-2">${minorsHTML}</ul>
            </div>
            <hr class="border-zinc-200 dark:border-zinc-700 my-6">
            <div class="flex flex-wrap items-center justify-between gap-2 mb-4">
                <h6 class="text-sm font-bold text-zinc-900 dark:text-white">Student Reviews</h6>
                <div id="reviewSummary" class="inline-flex items-center gap-1 rounded-full bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 px-3 py-1 text-xs text-amber-700 dark:text-amber-200 font-medium">Loading rating...</div>
            </div>
            <section id="ratingDistribution" class="hidden mb-6 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/60 p-4" aria-labelledby="ratingDistributionTitle"></section>
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
                ${window.ModuleGoAuth?.authenticated ? `
                <label class="mb-4 flex cursor-pointer items-start gap-3 rounded-xl border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/60">
                    <input id="reviewAnonymous" type="checkbox" checked class="mt-0.5 h-4 w-4 rounded border-zinc-300 text-primary-600 focus:ring-primary-500">
                    <span>
                        <span class="block text-sm font-semibold text-zinc-700 dark:text-zinc-200">Post anonymously</span>
                        <span class="block text-xs text-zinc-500 dark:text-zinc-400">Turn this off to show your display name.</span>
                    </span>
                </label>` : `
                <p class="mb-4 rounded-xl bg-zinc-50 px-3 py-2 text-xs text-zinc-500 dark:bg-zinc-800/60 dark:text-zinc-400">Guest reviews are shown as Anonymous student and remain editable in this browser for 30 days.</p>`}
                <div class="flex gap-3 pt-1">
                    <button id="submitReviewBtn" class="rounded-xl bg-primary-500 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all duration-300 hover:bg-primary-600 hover:shadow active:translate-y-0" type="button">Submit Review</button>
                    <button id="cancelEditReviewBtn" class="hidden rounded-xl border border-zinc-200 dark:border-zinc-700 px-6 py-3 text-sm font-semibold text-zinc-600 dark:text-zinc-400 transition-all duration-300 hover:border-zinc-300 dark:hover:border-zinc-600 hover:text-zinc-800 dark:hover:text-zinc-200 active:translate-y-0" type="button">Cancel edit</button>
                </div>
            </div>
        `;
    },

    /**
     * Fetch reviews for a module from the API and render them in the modal.
     * @param {string} moduleCode - The module code to load reviews for.
     */
    async loadReviews(moduleCode) {
        const reviewsList = document.getElementById('reviewsList');
        if (!reviewsList) return;

        try {
            const response = await fetch(`/api/reviews/${encodeURIComponent(moduleCode)}`);
            if (!response.ok) throw new Error('Failed to fetch reviews.');
            const reviews = await response.json();
            this.currentReviews = new Map(reviews.map(r => [r.id, r]));

            if (reviews.length === 0) {
                reviewsList.innerHTML = '<p class="text-sm text-zinc-400 dark:text-zinc-400 py-3">No reviews yet. Be the first!</p>';
                return;
            }

            // Fetch vote data for all reviews
            let votesData = {};
            try {
                const reviewIds = reviews.map(r => r.id);
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

            // Sort by highest vote score first, then newest
            reviews.sort((a, b) => {
                const aScore = (votesData[a.id]?.score || 0);
                const bScore = (votesData[b.id]?.score || 0);
                if (bScore !== aScore) return bScore - aScore;
                const aTime = parseTimestamp(a.created_at)?.getTime() || 0;
                const bTime = parseTimestamp(b.created_at)?.getTime() || 0;
                return bTime - aTime;
            });

            reviewsList.innerHTML = reviews.map(r => this.createReviewMarkup(r, votesData[r.id] || { score: 0, user_vote: 0 })).join('');
            reviewsList.querySelectorAll('.edit-review-btn').forEach(btn => {
                btn.addEventListener('click', () => this.startEditReview(Number(btn.dataset.reviewId)));
            });
            reviewsList.querySelectorAll('.delete-review-btn').forEach(btn => {
                btn.addEventListener('click', () => this.deleteReview(Number(btn.dataset.reviewId)));
            });
            reviewsList.querySelectorAll('.vote-btn').forEach(btn => {
                btn.addEventListener('click', () => this.handleVote(Number(btn.dataset.reviewId), Number(btn.dataset.vote)));
            });
            if (reviews.length > 3) {
                const existingBtn = reviewsList.parentNode.querySelector('[data-toggle="reviews"]');
                if (existingBtn) existingBtn.remove();
                const btn = document.createElement('button');
                btn.className = 'mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors';
                btn.dataset.toggle = 'reviews';
                btn.dataset.expanded = 'false';
                btn.innerHTML = `<span>Show all ${reviews.length} reviews</span><i data-lucide="chevron-down" class="w-3.5 h-3.5 transition-transform duration-200"></i>`;
                reviewsList.parentNode.insertBefore(btn, reviewsList.nextSibling);
                btn.addEventListener('click', () => {
                    const expanded = btn.dataset.expanded === 'true';
                    btn.dataset.expanded = (!expanded).toString();
                    const icon = btn.querySelector('i');
                    const label = btn.querySelector('span');
                    const items = document.querySelectorAll('#reviewsList > article');
                    if (!expanded) {
                        items.forEach(item => item.classList.remove('collapsible-hidden'));
                        label.textContent = 'Show fewer';
                        icon.classList.add('rotate-180');
                    } else {
                        items.forEach((item, i) => {
                            if (i >= 3) item.classList.add('collapsible-hidden');
                        });
                        label.textContent = `Show all ${items.length} reviews`;
                        icon.classList.remove('rotate-180');
                    }
                });
            } else {
                const existingBtn = reviewsList.parentNode.querySelector('[data-toggle="reviews"]');
                if (existingBtn) existingBtn.remove();
            }
            lucide.createIcons();
            this.initCollapsibles();
        } catch (error) {
            console.error('Error loading reviews:', error);
            reviewsList.innerHTML = '<p class="text-sm text-red-500 py-3">Could not load reviews.</p>';
        }
    },

    /**
     * Handle a vote action on a review.
     * @param {number} reviewId - The review to vote on.
     * @param {number} voteType - 1 for upvote, -1 for downvote.
     */
    async handleVote(reviewId, voteType) {
        const article = document.querySelector(`.review-item[data-review-id="${reviewId}"]`);
        const btn = article?.querySelector(`.vote-btn[data-vote="${voteType}"]`);
        if (btn) btn.disabled = true;
        try {
            const response = await apiFetch(`/api/reviews/${reviewId}/vote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vote_type: voteType }),
            });
            if (!response.ok) {
                const errBody = await response.text();
                console.error(`Vote failed: ${response.status} - ${errBody}`);
                throw new Error('Failed to vote.');
            }

            if (!article) return;

            const votesResponse = await fetch(`/api/reviews/${reviewId}/vote`);
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
            if (btn) btn.disabled = false;
        }
    },

    /**
     * Build the HTML for a single review card.
     * @param {Object} review - The review object from the API.
     * @param {Object} votes - Vote data {score, user_vote} for this review.
     * @returns {string} HTML string for the review.
     */
    createReviewMarkup(review, votes = { score: 0, user_vote: 0 }) {
        const comment = review.comment
            ? escapeHtml(review.comment)
            : '<span class="text-zinc-400 dark:text-zinc-400 italic">No written comment</span>';
        const updated = review.updated_at
            ? `<span class="ml-2 text-zinc-400 dark:text-zinc-400">Edited ${formatTimestamp(review.updated_at)}</span>`
            : '';
        const isOwner = review.is_owner === true;
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

        return `
            <article class="review-item" data-review-id="${review.id}">
                <div class="flex items-start justify-between gap-3 mb-2">
                    <div class="flex-1">
                        <div class="star-rating flex gap-0.5 text-sm mb-1.5" aria-label="${review.rating} out of 5 stars">
                            ${createStars(review.rating)}
                        </div>
                        <p class="mb-1 text-xs font-semibold text-zinc-500 dark:text-zinc-400">${escapeHtml(review.author?.label || 'Anonymous student')}</p>
                        <p class="text-sm text-zinc-700 dark:text-zinc-300">${comment}</p>
                    </div>
                    ${createReviewActionsHTML(review.id, isOwner)}
                </div>
                <div class="flex items-center gap-3">
                    <small class="text-xs text-zinc-400 dark:text-zinc-400">${formatTimestamp(review.created_at)}${updated}</small>
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
            </article>
        `;
    },

    /**
     * Render the review summary badge from the shared rating API data.
     * @param {Object} ratingSummary - Average, count, and distribution data.
     */
    renderReviewSummary(ratingSummary) {
        const summary = document.getElementById('reviewSummary');
        if (!summary) return;
        if (!ratingSummary.review_count) {
            summary.innerHTML = '<i data-lucide="star" class="w-4 h-4 mr-1 inline-block text-amber-400" aria-hidden="true"></i>No ratings yet';
            lucide.createIcons();
            return;
        }
        const label = ratingSummary.review_count === 1 ? 'review' : 'reviews';
        summary.innerHTML = `<i data-lucide="star" class="w-4 h-4 mr-1 inline-block fill-amber-400 text-amber-400" aria-hidden="true"></i><strong>${Number(ratingSummary.average_rating).toFixed(1)} average</strong><span aria-hidden="true">&middot;</span><span>${ratingSummary.review_count} ${label}</span>`;
        lucide.createIcons();
    },

    /**
     * Render five-to-one-star counts as proportional progress bars.
     * @param {Object} ratingSummary - Average, count, and distribution data.
     */
    renderRatingDistribution(ratingSummary) {
        const container = document.getElementById('ratingDistribution');
        if (!container) return;

        const total = Number(ratingSummary.review_count) || 0;
        if (total === 0) {
            container.innerHTML = '';
            container.classList.add('hidden');
            return;
        }

        const distribution = ratingSummary.distribution || {};
        const rows = [5, 4, 3, 2, 1].map(rating => {
            const count = Number(distribution[String(rating)]) || 0;
            const percentage = Math.min(100, Math.max(0, (count / total) * 100));
            return `
                <div class="grid grid-cols-[3rem_minmax(0,1fr)_2rem] items-center gap-3 text-xs">
                    <span class="inline-flex items-center gap-1 font-semibold text-zinc-600 dark:text-zinc-300">
                        ${rating}<i data-lucide="star" class="h-3.5 w-3.5 fill-amber-400 text-amber-400" aria-hidden="true"></i>
                    </span>
                    <div class="h-2.5 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700" role="progressbar" aria-label="${rating} stars: ${count} of ${total} reviews" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${count}">
                        <div class="h-full rounded-full bg-amber-400 transition-all duration-300" style="width: ${percentage.toFixed(2)}%"></div>
                    </div>
                    <span class="text-right font-medium tabular-nums text-zinc-600 dark:text-zinc-300">${count}</span>
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <h6 id="ratingDistributionTitle" class="mb-3 text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Rating breakdown</h6>
            <div class="space-y-2.5">${rows}</div>
        `;
        container.classList.remove('hidden');
        lucide.createIcons();
    },

    /**
     * Render the average badge and distribution for a module.
     * @param {string} moduleCode - Module whose rating data should be shown.
     */
    renderRatingInsights(moduleCode) {
        const ratingSummary = DataManager.getRatingSummary(moduleCode);
        this.renderReviewSummary(ratingSummary);
        this.renderRatingDistribution(ratingSummary);
    },

    /**
     * Switch the review form into edit mode, pre-filling the rating and
     * comment fields and showing the cancel button.
     * @param {number} reviewId - The ID of the review to edit.
     */
    startEditReview(reviewId) {
        const review = this.currentReviews.get(reviewId);
        if (!review) return;
        this.editingReviewId = reviewId;
        document.getElementById('reviewFormTitle').textContent = 'Edit Review';
        document.getElementById('reviewRating').value = String(review.rating);
        document.getElementById('reviewComment').value = review.comment;
        const anonymous = document.getElementById('reviewAnonymous');
        if (anonymous) anonymous.checked = review.author?.anonymous !== false;
        document.getElementById('submitReviewBtn').textContent = 'Save Changes';
        document.getElementById('cancelEditReviewBtn').classList.remove('hidden');
        clearElementMessage('reviewFormMessage');
        document.getElementById('reviewFormCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    /**
     * Reset the review form back to create mode.
     */
    resetReviewForm() {
        this.editingReviewId = null;
        document.getElementById('reviewFormTitle').textContent = 'Leave a Review';
        document.getElementById('reviewRating').value = '5';
        document.getElementById('reviewComment').value = '';
        const anonymous = document.getElementById('reviewAnonymous');
        if (anonymous) anonymous.checked = true;
        document.getElementById('submitReviewBtn').textContent = 'Submit Review';
        document.getElementById('cancelEditReviewBtn').classList.add('hidden');
        clearElementMessage('reviewFormMessage');
    },

    /**
     * Submit a new review or update an existing one, then refresh the
     * review list and rating display.
     * @param {string} moduleCode - The module code (used for new reviews).
     */
    async saveReview(moduleCode) {
        const rating = Number(document.getElementById('reviewRating').value);
        const comment = document.getElementById('reviewComment').value.trim();
        const button = document.getElementById('submitReviewBtn');
        const isEditing = this.editingReviewId !== null;
        const endpoint = isEditing ? `/api/reviews/${this.editingReviewId}` : '/api/reviews';
        const payload = { rating, comment };
        const anonymous = document.getElementById('reviewAnonymous');
        if (anonymous) payload.is_anonymous = anonymous.checked;
        if (!isEditing) payload.module_code = moduleCode;

        button.disabled = true;
        button.textContent = isEditing ? 'Saving...' : 'Submitting...';
        clearElementMessage('reviewFormMessage');

        try {
            const response = await apiFetch(endpoint, {
                method: isEditing ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok) {
                if (response.status === 409) {
                    const ownedReview = [...this.currentReviews.values()]
                        .find(review => review.is_owner);
                    if (ownedReview) this.startEditReview(ownedReview.id);
                }
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

    /**
     * Delete a review after confirmation, then refresh the views.
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
            if (this.editingReviewId === reviewId) this.resetReviewForm();
            await this.refreshReviewViews(this.currentModuleCode);
            showFormMessage('Review deleted.', 'success');
        } catch (error) {
            console.error('Error deleting review:', error);
            showFormMessage(error.message, 'danger');
        }
    },

    /**
     * Reload reviews and rating summaries, then update the UI.
     * @param {string} moduleCode - The module to refresh.
     */
    async refreshReviewViews(moduleCode) {
        try {
            await DataManager.refreshRatingSummaries();
        } catch (error) {
            console.error('Error refreshing rating summaries:', error);
        }
        this.renderRatingInsights(moduleCode);
        await this.loadReviews(moduleCode);
        if (typeof UIRenderer !== 'undefined') {
            UIRenderer.updateRatingDisplay(moduleCode);
        }
        document.dispatchEvent(new CustomEvent('ratings:changed', {
            detail: { moduleCode },
        }));
    },

    initCollapsibles() {
        document.querySelectorAll('#diplomasList > li:nth-child(n+4)').forEach(item => {
            item.classList.add('collapsible-hidden');
        });
        document.querySelectorAll('#reviewsList > article:nth-child(n+4)').forEach(item => {
            item.classList.add('collapsible-hidden');
        });
    },
};

/* ── Private helper functions (module scope) ────────────────────────── */

/**
 * Display a message in the review form's message area.
 * @param {string} message - The message text.
 * @param {'success'|'danger'} type - The message type.
 */
function showFormMessage(message, type) {
    const el = document.getElementById('reviewFormMessage');
    if (el) showMessage(el, message, type);
}

/**
 * Clear the review form's message area.
 * @param {string} elementId - The ID of the message element.
 */
function clearElementMessage(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = '';
        el.className = 'hidden mb-3 rounded-lg px-4 py-2.5 text-sm';
    }
}

/**
 * Format a timestamp string for display in review cards.
 * @param {string} value - ISO or space-separated timestamp.
 * @returns {string} Formatted date string, or the raw value if unparseable.
 */
function formatTimestamp(value) {
    const date = parseTimestamp(value);
    return date ? formatReviewDate(date) : escapeHtml(value);
}

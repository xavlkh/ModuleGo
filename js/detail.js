const DetailManager = {
    modal: null,

    init() {
        this.modal = new bootstrap.Modal(document.getElementById('moduleModal'));
    },

    showModuleDetail(moduleCode) {
        const module = DataManager.getModule(moduleCode);
        if (!module) return;

        const modalBody = document.getElementById('moduleModalBody');
        const modalTitle = document.getElementById('moduleModalLabel');
        
        modalTitle.textContent = `${module.code} - ${module.name}`;

        modalBody.innerHTML = this.createDetailContent(module);

        this.modal.show();
    },

    createDetailContent(module) {
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

            <div class="mt-4">
                <a href="${module.url}" target="_blank" class="btn btn-outline-primary">
                    <i class="bi bi-box-arrow-up-right me-2"></i>View on RP Website
                </a>
            </div>
        `;
    }
};

// Starts the home page app.
const App = {
    async init() {
        try {
            // Set up UI controllers before loading data.
            UIRenderer.init();
            SearchManager.init();
            DetailManager.init();

            UIRenderer.showLoading();
            
            await DataManager.loadData();
            
            // Show an initial sample of modules.
            UIRenderer.updateModuleCount(DataManager.modules.length);
            UIRenderer.renderResults(DataManager.modules.slice(0, 20));
            UIRenderer.updateResultsCount(Math.min(20, DataManager.modules.length));
            
        } catch (error) {
            // Show a friendly error if data cannot load.
            console.error('Failed to initialize app:', error);
            const spinner = document.getElementById('loadingSpinner');
            if (spinner) spinner.classList.add('d-none');
            document.getElementById('resultsContainer').innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-exclamation-triangle display-1 text-danger"></i>
                    <h3 class="mt-3 text-danger">Failed to load module data</h3>
                    <p class="text-muted">Please refresh the page or try again later.</p>
                </div>
            `;
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// #5 Export / Share
const ShareManager = {
    getShareUrl() {
        const params = new URLSearchParams(window.location.search);
        // Grab current filters from UI
        const school = document.getElementById('schoolFilter')?.value || 'all';
        const diploma = document.getElementById('diplomaFilter')?.value || 'all';
        const rating = document.getElementById('ratingFilter')?.value || 'all';
        const career = document.getElementById('careerFilter')?.value || 'all';
        const q = document.getElementById('searchInput')?.value || '';

        if (q) params.set('q', q);
        if (school!== 'all') params.set('school', school);
        else params.delete('school');
        if (diploma!== 'all') params.set('diploma', diploma);
        else params.delete('diploma');
        if (rating!== 'all') params.set('rating', rating);
        else params.delete('rating');
        if (career!== 'all') params.set('career', career);
        else params.delete('career');

        return `${window.location.origin}${window.location.pathname}?${params.toString()}`;
    },

    async copyLink() {
        const url = this.getShareUrl();
        try {
            await navigator.clipboard.writeText(url);
            this.showToast("✅ Link copied! Share it with your friend");
            // Update URL bar without reload
            history.replaceState(null, '', url);
        } catch {
            // Fallback
            const input = document.createElement('input');
            input.value = url;
            document.body.appendChild(input);
            input.select();
            document.execCommand('copy');
            document.body.removeChild(input);
            this.showToast("✅ Link copied!");
        }
    },

    exportCSV() {
        if (!DataManager ||!DataManager.modules) return;
        // Get currently filtered results from UI or DataManager
        const filtered = window.currentFilteredModules || DataManager.modules.slice(0, 100);

        if (filtered.length === 0) {
            this.showToast("⚠️ No modules to export");
            return;
        }

        const headers = ["Code", "Name", "School", "Rating", "Reviews"];
        const rows = filtered.map(m => {
            const rating = DataManager.getRatingSummary(m.code);
            return [
                `"${m.code}"`,
                `"${(m.name || '').replace(/"/g, '""')}"`,
                `"${m.school || ''}"`,
                rating.average_rating || 'N/A',
                rating.review_count || 0
            ].join(',');
        });

        const csv = [headers.join(','),...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `modulego-export-${new Date().toISOString().slice(0,10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        this.showToast(`📄 Exported ${filtered.length} modules`);
    },

    showToast(msg) {
        let toast = document.getElementById('share-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'share-toast';
            toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1f1f1f;color:white;padding:10px 16px;border-radius:24px;font-size:13px;z-index:10001;box-shadow:0 4px 12px rgba(0,0,0,0.2);transition:all 0.3s';
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.style.opacity = '1';
        toast.style.bottom = '80px';
        setTimeout(() => { toast.style.opacity = '0'; toast.style.bottom = '60px'; }, 2500);
    }
};
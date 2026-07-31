/**
 * Share and export functionality for filtered module lists.
 * Handles URL sharing and CSV export.
 * @module share
 */
const ShareManager = {
    getShareUrl() {
        const params = new URLSearchParams(window.location.search);
        const school = document.getElementById('schoolFilter')?.value || 'all';
        const diploma = document.getElementById('diplomaFilter')?.value || 'all';
        const minor = document.getElementById('minorFilter')?.value || 'all';
        const rating = document.getElementById('ratingFilter')?.value || 'all';
        const career = document.getElementById('careerFilter')?.value || 'all';
        const q = document.getElementById('searchInput')?.value || '';

        if (q) params.set('q', q);
        if (school !== 'all') params.set('school', school);
        else params.delete('school');
        if (diploma !== 'all') params.set('diploma', diploma);
        else params.delete('diploma');
        if (minor !== 'all') params.set('minor', minor);
        else params.delete('minor');
        if (rating !== 'all') params.set('rating', rating);
        else params.delete('rating');
        if (career !== 'all') params.set('career', career);
        else params.delete('career');

        return `${window.location.origin}${window.location.pathname}?${params.toString()}`;
    },

    async copyLink(btn) {
        const url = this.getShareUrl();
        try {
            await navigator.clipboard.writeText(url);
        } catch {
            const input = document.createElement('input');
            input.value = url;
            document.body.appendChild(input);
            input.select();
            document.execCommand('copy');
            document.body.removeChild(input);
        }
        history.replaceState(null, '', url);
        if (btn) {
            const original = btn.innerHTML;
            btn.innerHTML = '<i data-lucide="check" class="h-3.5 w-3.5"></i>Copied!';
            btn.disabled = true;
            lucide.createIcons();
            setTimeout(() => {
                btn.innerHTML = original;
                btn.disabled = false;
                lucide.createIcons();
            }, 2000);
        }
    },

    exportCSV() {
        if (!DataManager || !DataManager.modules || DataManager.modules.length === 0) {
            this.showToast('No modules to export');
            return;
        }

        const headers = ['Code', 'Name', 'School', 'Synopsis', 'URL', 'Diplomas', 'Minors'];
        const rows = DataManager.modules.map(m => {
            const rawDiplomas = DataManager.getDiplomasByModule(m.code);
            // Merge same diploma + category
            const merged = new Map();
            for (const d of rawDiplomas) {
                const key = `${d.course_code}||${d.category}`;
                if (merged.has(key)) {
                    const existing = merged.get(key);
                    if (d.major_name && !existing.majorNames.includes(d.major_name)) {
                        existing.majorNames.push(d.major_name);
                    }
                } else {
                    merged.set(key, { ...d, majorNames: d.major_name ? [d.major_name] : [] });
                }
            }
            const diplomas = [...merged.values()];
            const diplomaStr = diplomas.map(d => {
                if (d.category === 'Major' && d.majorNames.length > 0) {
                    return `${d.course_code} (Major: ${d.majorNames.join('; ')})`;
                }
                return `${d.course_code} (${d.category})`;
            }).join('; ');
            const minors = DataManager.getMinorsByModule(m.code);
            const minorStr = minors.map(min => min.minor_name).join('; ');
            return [
                `"${m.code}"`,
                `"${(m.name || '').replace(/"/g, '""')}"`,
                `"${m.school || ''}"`,
                `"${(m.synopsis || '').replace(/"/g, '""')}"`,
                `"${m.url || ''}"`,
                `"${diplomaStr.replace(/"/g, '""')}"`,
                `"${minorStr.replace(/"/g, '""')}"`,
            ].join(',');
        });

        const csv = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `modulego-modules-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        this.showToast(`Exported ${DataManager.modules.length} modules`);
    },

    showToast(msg) {
        let toast = document.getElementById('share-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'share-toast';
            toast.className = 'fixed bottom-20 left-1/2 -translate-x-1/2 z-[10001] rounded-full bg-zinc-800 dark:bg-zinc-700 text-white px-4 py-2.5 text-sm shadow-lg transition-all duration-300';
            document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.style.opacity = '1';
        setTimeout(() => { toast.style.opacity = '0'; }, 2500);
    },
};
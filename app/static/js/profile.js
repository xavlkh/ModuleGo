/**
 * Account profile page: password change and account deletion.
 * @module profile
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('deleteAccountForm');
    if (!form) return;

    const passwordInput = form.querySelector('[name="current_password"]');
    const tokenInput = document.getElementById('deleteAccountToken');
    const submitButton = document.getElementById('deleteAccountButton');
    const errorMessage = document.getElementById('deleteAccountError');

    const showError = (message) => {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    };

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        errorMessage.classList.add('hidden');
        submitButton.disabled = true;

        try {
            const response = await fetch(form.dataset.verifyUrl, {
                method: 'POST',
                body: new FormData(form),
                headers: { Accept: 'application/json' },
            });
            const result = await response.json();
            if (!response.ok || !result.verified) {
                showError(result.message || 'Could not verify your password.');
                return;
            }

            if (!window.confirm('Delete this account permanently?')) return;

            tokenInput.value = result.confirmation_token;
            passwordInput.value = '';
            form.action = form.dataset.deleteUrl;
            HTMLFormElement.prototype.submit.call(form);
        } catch (_error) {
            showError('Could not verify your password. Please try again.');
        } finally {
            submitButton.disabled = false;
        }
    });
});

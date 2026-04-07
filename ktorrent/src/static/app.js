// Flash auto-dismiss after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
    const alerts = document.querySelectorAll('.flash-alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Passkey show/hide toggle
    const passkeyToggle = document.getElementById('passkey-toggle');
    const passkeyInput = document.getElementById('passkey-input');
    if (passkeyToggle && passkeyInput) {
        passkeyToggle.addEventListener('click', function () {
            if (passkeyInput.type === 'password') {
                passkeyInput.type = 'text';
                passkeyToggle.textContent = 'Hide';
            } else {
                passkeyInput.type = 'password';
                passkeyToggle.textContent = 'Show';
            }
        });
    }

    // Confirm dialogs for destructive actions
    document.querySelectorAll('[data-confirm]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            if (!confirm(el.getAttribute('data-confirm'))) {
                e.preventDefault();
            }
        });
    });
});

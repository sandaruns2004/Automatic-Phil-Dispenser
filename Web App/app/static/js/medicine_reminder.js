document.addEventListener('DOMContentLoaded', () => {
    const takeDoseButtons = document.querySelectorAll('.take-dose-btn');

    function showNotification(message, type = 'info') {
        const notificationContainer = document.getElementById('notification-container');
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : 'success'} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>`;
        const toastElement = document.createElement('div');
        toastElement.innerHTML = toastHtml;
        notificationContainer.appendChild(toastElement);
        const toast = new bootstrap.Toast(toastElement.querySelector('.toast'));
        toast.show();
        toastElement.querySelector('.toast').addEventListener('hidden.bs.toast', () => toastElement.remove());
    }

    takeDoseButtons.forEach(button => {
        button.addEventListener('click', () => {
            const row = button.closest('tr');
            const medicineId = row.dataset.medicineId;
            const remainingCountSpan = row.querySelector('.remaining-count');

            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Taking...';

            fetch(`/api/medicine/take/${medicineId}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        showNotification(data.message, 'success');
                        remainingCountSpan.textContent = data.remaining;
                        if (data.remaining == 0) {
                            button.disabled = true;
                            button.textContent = 'Out of Stock';
                        } else {
                            button.disabled = false;
                            button.textContent = 'Take Dose';
                        }
                    } else {
                        showNotification(data.message, 'error');
                        button.disabled = false;
                        button.textContent = 'Take Dose';
                    }
                })
                .catch(error => {
                    showNotification('An error occurred.', 'error');
                    console.error('Error:', error);
                    button.disabled = false;
                    button.textContent = 'Take Dose';
                });
        });
    });
});

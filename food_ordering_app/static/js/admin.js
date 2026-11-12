/**
 * Script hỗ trợ giao diện quản trị Admin Bếp Việt
 */
document.addEventListener('DOMContentLoaded', () => {
    // Tự động ẩn các alert sau 4 giây
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 4000);
    });
});

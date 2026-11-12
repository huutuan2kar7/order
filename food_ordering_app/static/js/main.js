/**
 * Quản lý giỏ hàng phía Client bằng localStorage
 */
class CartManager {
    constructor() {
        this.storageKey = 'food_cart_items_v1';
        this.items = this.loadCart();
        this.updateBadge();
        this.bindEvents();
    }

    loadCart() {
        try {
            const data = localStorage.getItem(this.storageKey);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            console.error('Lỗi đọc giỏ hàng từ localStorage:', e);
            return [];
        }
    }

    saveCart() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.items));
            this.updateBadge();
            this.renderDrawer();
        } catch (e) {
            console.error('Lỗi ghi giỏ hàng vào localStorage:', e);
        }
    }

    getItems() {
        return this.items;
    }

    addItem(food) {
        const existing = this.items.find(item => item.id === food.id);
        if (existing) {
            existing.quantity += 1;
        } else {
            this.items.push({
                id: food.id,
                name: food.name,
                price: parseFloat(food.price),
                image: food.image,
                quantity: 1
            });
        }
        this.saveCart();
        this.showToast(`Đã thêm "${food.name}" vào giỏ hàng!`);
    }

    updateQuantity(foodId, change) {
        const item = this.items.find(item => item.id === foodId);
        if (!item) return;

        item.quantity += change;
        if (item.quantity <= 0) {
            this.items = this.items.filter(i => i.id !== foodId);
        }
        this.saveCart();
        this.renderCartPage();
    }

    removeItem(foodId) {
        this.items = this.items.filter(i => i.id !== foodId);
        this.saveCart();
        this.renderCartPage();
    }

    clearCart() {
        if (confirm('Bạn có chắc muốn xóa sạch toàn bộ giỏ hàng không?')) {
            this.clearCartSilently();
            this.renderCartPage();
        }
    }

    clearCartSilently() {
        this.items = [];
        this.saveCart();
    }

    getTotalPrice() {
        return this.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    }

    getTotalCount() {
        return this.items.reduce((sum, item) => sum + item.quantity, 0);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('vi-VN').format(amount) + ' đ';
    }

    updateBadge() {
        const badge = document.getElementById('cartCountBadge');
        if (badge) {
            const count = this.getTotalCount();
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    }

    showToast(message) {
        const toastEl = document.getElementById('cartToast');
        if (toastEl) {
            const msgEl = document.getElementById('toastMessage');
            if (msgEl) msgEl.textContent = message;
            const toast = new bootstrap.Toast(toastEl, { delay: 2500 });
            toast.show();
        }
    }

    renderDrawer() {
        const container = document.getElementById('drawerCartItems');
        const emptyNotice = document.getElementById('drawerEmptyNotice');
        const footer = document.getElementById('drawerCartFooter');
        const totalEl = document.getElementById('drawerCartTotal');

        if (!container) return;

        if (this.items.length === 0) {
            if (emptyNotice) emptyNotice.style.display = 'block';
            if (footer) footer.style.display = 'none';
            // Xóa các món cũ
            const oldItems = container.querySelectorAll('.drawer-item');
            oldItems.forEach(el => el.remove());
            return;
        }

        if (emptyNotice) emptyNotice.style.display = 'none';
        if (footer) footer.style.display = 'block';
        if (totalEl) totalEl.textContent = this.formatCurrency(this.getTotalPrice());

        // Render danh sách món
        let html = '';
        this.items.forEach(item => {
            html += `
                <div class="drawer-item d-flex gap-3 mb-3 p-2 bg-white rounded-3 border align-items-center">
                    <img src="${item.image}" alt="${item.name}" class="rounded-2" style="width: 50px; height: 50px; object-fit: cover;">
                    <div class="flex-grow-1">
                        <div class="fw-bold small text-truncate" style="max-width: 150px;">${item.name}</div>
                        <div class="text-orange small fw-semibold">${this.formatCurrency(item.price)}</div>
                    </div>
                    <div class="d-flex align-items-center gap-1">
                        <button class="btn btn-sm btn-light border p-1 px-2" onclick="cartManager.updateQuantity(${item.id}, -1)">-</button>
                        <span class="small fw-bold px-1">${item.quantity}</span>
                        <button class="btn btn-sm btn-light border p-1 px-2" onclick="cartManager.updateQuantity(${item.id}, 1)">+</button>
                    </div>
                </div>
            `;
        });

        // Xóa các món cũ và thêm mới
        const oldItems = container.querySelectorAll('.drawer-item');
        oldItems.forEach(el => el.remove());
        container.insertAdjacentHTML('beforeend', html);
    }

    renderCartPage() {
        const listContainer = document.getElementById('cartItemsList');
        const emptyMsg = document.getElementById('cartEmptyMessage');
        const subtotalEl = document.getElementById('summarySubtotal');
        const totalEl = document.getElementById('summaryTotal');
        const btnSubmit = document.getElementById('btnPlaceOrder');

        if (!listContainer) return;

        if (this.items.length === 0) {
            listContainer.style.display = 'none';
            if (emptyMsg) emptyMsg.style.display = 'block';
            if (btnSubmit) btnSubmit.disabled = true;
            if (subtotalEl) subtotalEl.textContent = '0 đ';
            if (totalEl) totalEl.textContent = '0 đ';
            return;
        }

        listContainer.style.display = 'block';
        if (emptyMsg) emptyMsg.style.display = 'none';
        if (btnSubmit) btnSubmit.disabled = false;

        const total = this.getTotalPrice();
        if (subtotalEl) subtotalEl.textContent = this.formatCurrency(total);
        if (totalEl) totalEl.textContent = this.formatCurrency(total);

        let html = '<div class="table-responsive"><table class="table align-middle"><tbody>';
        this.items.forEach(item => {
            html += `
                <tr>
                    <td style="width: 70px;">
                        <img src="${item.image}" alt="${item.name}" class="rounded-3 shadow-sm" style="width: 60px; height: 60px; object-fit: cover;">
                    </td>
                    <td>
                        <div class="fw-bold text-dark">${item.name}</div>
                        <div class="text-muted small">${this.formatCurrency(item.price)}</div>
                    </td>
                    <td class="text-center" style="width: 140px;">
                        <div class="input-group input-group-sm">
                            <button class="btn btn-outline-secondary" type="button" onclick="cartManager.updateQuantity(${item.id}, -1)">-</button>
                            <input type="text" class="form-control text-center bg-white" value="${item.quantity}" readonly>
                            <button class="btn btn-outline-secondary" type="button" onclick="cartManager.updateQuantity(${item.id}, 1)">+</button>
                        </div>
                    </td>
                    <td class="text-end fw-bold text-orange" style="width: 110px;">
                        ${this.formatCurrency(item.price * item.quantity)}
                    </td>
                    <td class="text-center" style="width: 45px;">
                        <button class="btn btn-sm text-danger border-0" onclick="cartManager.removeItem(${item.id})" title="Xóa món">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        html += '</tbody></table></div>';
        listContainer.innerHTML = html;
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.add-to-cart-btn');
            if (btn) {
                const food = {
                    id: parseInt(btn.dataset.id),
                    name: btn.dataset.name,
                    price: btn.dataset.price,
                    image: btn.dataset.image
                };
                this.addItem(food);
            }
        });

        const openBtn = document.getElementById('openCartBtn');
        if (openBtn) {
            openBtn.addEventListener('click', () => {
                this.renderDrawer();
            });
        }
    }
}

// Khởi tạo global instance
const cartManager = new CartManager();

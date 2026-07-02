// cart.js — Premium Music Producer Cart (Single License, No Qty)
(function() {
    'use strict';

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCart);
    } else {
        initCart();
    }

    function initCart() {
        const $ = (id) => document.getElementById(id);

        const els = {
            drawer: $('cartDrawer'),
            overlay: $('cartOverlay'),
            openBtn: $('openCartBtn'),
            closeBtn: $('closeCartBtn'),
            itemsList: $('cartItemsList'),
            subtotal: $('cartSubtotal') || $('cartTotalAmount'),
            grandTotal: $('cartGrandTotal'),
            cartCount: $('cartCount'),
            itemsCount: $('cartItemsCount'),
            checkoutBtn: $('checkoutBtn'),
            emptyState: $('emptyCartState'),
            suggestions: $('cartSuggestions'),
            footer: $('cartFooter'),
            toastContainer: $('toastContainer')
        };

        if (!els.drawer) { console.error('[CART] #cartDrawer missing'); return; }
        if (!els.openBtn) { console.error('[CART] #openCartBtn missing'); return; }

        let cart = [];
        let pendingCheckoutItems = null;
        let isProcessing = false;

        try {
            const raw = localStorage.getItem('xlovebeats_cart');
            cart = raw ? JSON.parse(raw) : [];
            if (!Array.isArray(cart)) cart = [];
        } catch (e) { cart = []; }

        if (!els.toastContainer) {
            const tc = document.createElement('div');
            tc.id = 'toastContainer';
            tc.className = 'toast-container';
            document.body.appendChild(tc);
            els.toastContainer = tc;
        }

        const formatPrice = (n) => '₹' + (parseFloat(n) || 0).toFixed(2);
        const saveCart = () => {
            try { localStorage.setItem('xlovebeats_cart', JSON.stringify(cart)); } catch (e) {}
        };

        function showToast(message, type = 'success') {
            if (!els.toastContainer) return;
            const icons = {
                success: 'fa-check',
                error: 'fa-exclamation-circle',
                info: 'fa-info-circle',
                warning: 'fa-exclamation-triangle'
            };
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.innerHTML = `
                <div class="toast-icon"><i class="fas ${icons[type] || icons.success}"></i></div>
                <span>${message}</span>
            `;
            els.toastContainer.appendChild(toast);
            setTimeout(() => {
                toast.classList.add('toast-out');
                toast.addEventListener('animationend', () => toast.remove(), { once: true });
            }, 2800);
        }

        function popBadge() {
            if (!els.cartCount) return;
            els.cartCount.classList.remove('badge-pop');
            void els.cartCount.offsetWidth;
            els.cartCount.classList.add('badge-pop');
            setTimeout(() => els.cartCount.classList.remove('badge-pop'), 500);
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function renderEmptyState() {
            if (!els.itemsList) return;
            els.itemsList.innerHTML = '';
            const empty = document.createElement('div');
            empty.className = 'empty-cart-state';
            empty.id = 'emptyCartState';
            empty.innerHTML = `
                <div class="empty-cart-vinyl">
                    <div class="empty-vinyl-grooves"></div>
                    <i class="fas fa-music"></i>
                </div>
                <p class="empty-cart-title">Your cart is empty</p>
                <p class="empty-cart-subtitle">Drop some fire beats in here 🔥</p>
                <button class="empty-cart-cta" id="browseBeatsBtn">Browse Beats</button>
            `;
            els.itemsList.appendChild(empty);
            const btn = empty.querySelector('#browseBeatsBtn');
            if (btn) {
                btn.addEventListener('click', () => {
                    closeCart();
                    setTimeout(() => {
                        const tab = document.querySelector('[data-tab="beat-packs"]');
                        if (tab) tab.click();
                        const section = document.getElementById('beat-packs');
                        if (section) section.scrollIntoView({ behavior: 'smooth' });
                    }, 300);
                });
            }
        }

        function updateCartUI() {
            if (!els.itemsList) return;

            const count = cart.length;
            const total = cart.reduce((sum, item) => sum + (parseFloat(item.price) || 0), 0);

            if (els.cartCount) {
                const old = parseInt(els.cartCount.textContent) || 0;
                els.cartCount.textContent = count;
                if (count > old) popBadge();
            }
                    // Mobile nav cart badge
        const mobileBadge = document.getElementById('mobileCartCount');
        if (mobileBadge) {
            if (count > 0) {
                mobileBadge.textContent = count > 9 ? '9+' : count;
                mobileBadge.style.display = 'flex';
            } else {
                mobileBadge.style.display = 'none';
            }
        }
            if (els.itemsCount) els.itemsCount.textContent = `${count} item${count !== 1 ? 's' : ''}`;

            if (count === 0) {
                renderEmptyState();
                if (els.checkoutBtn) els.checkoutBtn.disabled = true;
                if (els.subtotal) els.subtotal.textContent = formatPrice(0);
                if (els.grandTotal) els.grandTotal.textContent = formatPrice(0);
                if (els.footer) els.footer.style.opacity = '0.6';
                if (els.suggestions) els.suggestions.style.display = 'block';
                saveCart();
                return;
            }

            if (els.suggestions) els.suggestions.style.display = 'none';
            if (els.footer) els.footer.style.opacity = '1';
            if (els.checkoutBtn) els.checkoutBtn.disabled = false;

            els.itemsList.innerHTML = '';
            cart.forEach((item, index) => {
                const cfg = {
                    pack: { cls: 'pack', label: 'Pack', icon: 'fa-compact-disc' },
                    preset: { cls: 'preset', label: 'Preset', icon: 'fa-microphone-alt' },
                    single: { cls: 'single', label: 'Single', icon: 'fa-music' }
                }[item.type] || { cls: 'single', label: 'Single', icon: 'fa-music' };

                const div = document.createElement('div');
                div.className = 'cart-item';
                div.style.animationDelay = `${index * 0.06}s`;
                div.innerHTML = `
                    <div class="cart-item-thumb">
                        ${item.image ? `<img src="${item.image}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">` : ''}
                        <div class="thumb-placeholder" ${item.image ? 'style="display:none"' : ''}>
                            <i class="fas ${cfg.icon}"></i>
                        </div>
                    </div>
                    <div class="cart-item-info">
                        <div class="cart-item-name">${escapeHtml(item.name)}</div>
                        <div class="cart-item-meta">
                            <span class="cart-item-type ${cfg.cls}">${cfg.label}</span>
                            ${item.license ? `<span class="cart-item-license">${escapeHtml(item.license)} License</span>` : ''}
                        </div>
                    </div>
                    <div class="cart-item-right">
                        <div class="cart-item-price">${formatPrice(item.price)}</div>
                        <button class="remove-item" data-index="${index}" title="Remove">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `;
                els.itemsList.appendChild(div);
            });

            if (els.subtotal) els.subtotal.textContent = formatPrice(total);
            if (els.grandTotal) els.grandTotal.textContent = formatPrice(total);
            saveCart();
        }

        function openCart() {
            els.drawer.classList.add('open');
            if (els.overlay) els.overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function closeCart() {
            els.drawer.classList.remove('open');
            if (els.overlay) els.overlay.classList.remove('active');
            document.body.style.overflow = '';
        }

        function addItem(item) {
            const exists = cart.find(i => i.id === item.id && i.license === item.license);
            if (exists) {
                showToast('⚠️ Already in cart', 'warning');
                openCart();
                return;
            }
            cart.push(item);
            showToast(`🛒 ${item.name} added to cart!`, 'success');
            updateCartUI();
            openCart();
        }

        function removeItem(index) {
            const items = els.itemsList.querySelectorAll('.cart-item');
            if (items[index]) {
                items[index].classList.add('removing');
                items[index].addEventListener('animationend', () => {
                    cart.splice(index, 1);
                    updateCartUI();
                }, { once: true });
            } else {
                cart.splice(index, 1);
                updateCartUI();
            }
        }

        window.addToGlobalCart = function(item, isBuyNow = false) {
            addItem(item);
            if (isBuyNow) {
                setTimeout(() => {
                    if (els.checkoutBtn && !els.checkoutBtn.disabled) {
                        els.checkoutBtn.click();
                    }
                }, 400);
            }
        };

        window.removeFromCart = function(index) {
            removeItem(index);
        };

        window.clearCart = function() {
            cart = [];
            updateCartUI();
            showToast('Cart cleared', 'info');
        };

        async function checkIfUserLoggedIn() {
            try {
                const res = await fetch('/api/auth/me');
                const data = await res.json();
                return data.logged_in || false;
            } catch (err) { return false; }
        }

        function showLoginModal() {
            const modal = $('loginModal');
            if (!modal) return;
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
            const sub = modal.querySelector('.auth-modal-header p');
            if (sub) {
                if (!sub.dataset.originalText) sub.dataset.originalText = sub.textContent;
                sub.textContent = 'Please login to complete your purchase';
                sub.style.color = 'var(--accent-soft)';
            }
        }

        function restoreLoginModal() {
            const modal = $('loginModal');
            if (!modal) return;
            const sub = modal.querySelector('.auth-modal-header p');
            if (sub && sub.dataset.originalText) {
                sub.textContent = sub.dataset.originalText;
                sub.style.color = '';
            }
        }

        async function initiateCheckout(itemsToCheckout) {
            if (!itemsToCheckout || itemsToCheckout.length === 0 || isProcessing) return;
            isProcessing = true;

            const isLoggedIn = await checkIfUserLoggedIn();
            if (!isLoggedIn) {
                closeCart();
                pendingCheckoutItems = itemsToCheckout;
                showLoginModal();
                showToast('🔐 Login required to checkout', 'warning');
                isProcessing = false;
                return;
            }

            await proceedWithPayment(itemsToCheckout);
            isProcessing = false;
        }

        async function proceedWithPayment(itemsToCheckout) {
            if (typeof Razorpay === 'undefined') {
                showToast('Payment system unavailable. Please refresh.', 'error');
                return;
            }

            const exclusiveItems = itemsToCheckout.filter(i => i.license === 'exclusive');
            if (exclusiveItems.length > 0) {
                const names = exclusiveItems.map(i => i.name).join(', ');
                const msg = `Hello, I am interested in buying the Exclusive License for: ${names}. Please let me know the price.`;
                window.open(`https://wa.me/918329189796?text=${encodeURIComponent(msg)}`, '_blank');
                showToast('📱 Redirecting to WhatsApp...', 'info');
                exclusiveItems.forEach(item => {
                    const idx = cart.findIndex(i => i.id === item.id && i.license === item.license);
                    if (idx > -1) cart.splice(idx, 1);
                });
                updateCartUI();
                closeCart();
                return;
            }

            const origHTML = els.checkoutBtn ? els.checkoutBtn.innerHTML : '';
            if (els.checkoutBtn) {
                els.checkoutBtn.innerHTML = '<span class="checkout-btn-content"><i class="fas fa-spinner fa-spin"></i><span>Processing...</span></span>';
                els.checkoutBtn.disabled = true;
            }

            try {
                const res = await fetch('/api/create-razorpay-order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ items: itemsToCheckout })
                });

                const orderData = await res.json();
                if (orderData.error) throw new Error(orderData.error);

                               // ── BYPASS MODE: Skip Razorpay, verify directly ──
                if (orderData.bypass) {
                    const verifyRes = await fetch('/api/verify-razorpay-payment', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            db_order_id: orderData.db_order_id
                        })
                    });

                    const verifyData = await verifyRes.json();
                    if (verifyData.status === 'success') {
                        showToast('✅ Payment Successful! (Test Mode)', 'success');
                        itemsToCheckout.forEach(item => {
                            const idx = cart.findIndex(i => i.id === item.id && i.license === item.license);
                            if (idx > -1) cart.splice(idx, 1);
                        });
                        updateCartUI();
                        closeCart();
                        window.location.href = '/checkout/success?order_id=' + orderData.db_order_id;
                    } else {
                        showToast('❌ Verification failed', 'error');
                    }
                    return;
                }

                const options = {
                    key: orderData.key_id,
                    amount: orderData.amount,
                    currency: orderData.currency,
                    name: 'XLOVEBEATS',
                    description: 'Purchase Beats & Presets',
                    order_id: orderData.order_id,
                    handler: async function(response) {
                        const verifyRes = await fetch('/api/verify-razorpay-payment', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                razorpay_payment_id: response.razorpay_payment_id,
                                razorpay_order_id: response.razorpay_order_id,
                                razorpay_signature: response.razorpay_signature,
                                db_order_id: orderData.db_order_id
                            })
                        });

                        const verifyData = await verifyRes.json();
                        if (verifyData.status === 'success') {
                            showToast('✅ Payment Successful!', 'success');
                            itemsToCheckout.forEach(item => {
                                const idx = cart.findIndex(i => i.id === item.id && i.license === item.license);
                                if (idx > -1) cart.splice(idx, 1);
                            });
                            updateCartUI();
                            closeCart();
                            window.location.href = '/checkout/success?order_id=' + orderData.db_order_id;
                        } else {
                            showToast('❌ Verification failed', 'error');
                        }
                    },
                    theme: { color: '#7C8DF0' }
                };

                const rzp = new Razorpay(options);
                rzp.on('payment.failed', function(response) {
                    showToast('❌ Payment failed: ' + response.error.description, 'error');
                });
                rzp.open();

            } catch (error) {
                console.error(error);
                showToast('❌ Checkout failed: ' + error.message, 'error');
            } finally {
                if (els.checkoutBtn) {
                    els.checkoutBtn.innerHTML = origHTML;
                    els.checkoutBtn.disabled = cart.length === 0;
                }
            }
        }

        window.resumeCheckoutAfterLogin = async function() {
            if (!pendingCheckoutItems || pendingCheckoutItems.length === 0) return;
            restoreLoginModal();
            const items = pendingCheckoutItems;
            pendingCheckoutItems = null;

            setTimeout(async () => {
                const isLoggedIn = await checkIfUserLoggedIn();
                if (isLoggedIn) {
                    showToast('✅ Login successful! Resuming...', 'success');
                    openCart();
                    await proceedWithPayment(items);
                } else {
                    showToast('❌ Login failed. Try again.', 'error');
                }
            }, 500);
        };

        // Events
        els.openBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            openCart();
        });

                // Mobile cart button
        const mobileCartBtn = document.getElementById('mobileCartBtn');
        if (mobileCartBtn) {
            mobileCartBtn.addEventListener('click', function(e) {
                e.preventDefault();
                openCart();
            });
        }

        if (els.closeBtn) {
            els.closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                closeCart();
            });
        }

        if (els.overlay) els.overlay.addEventListener('click', closeCart);

        if (els.itemsList) {
            els.itemsList.addEventListener('click', (e) => {
                const btn = e.target.closest('.remove-item');
                if (btn) {
                    const idx = parseInt(btn.dataset.index);
                    if (!isNaN(idx)) removeItem(idx);
                }
            });
        }

        if (els.checkoutBtn) {
            els.checkoutBtn.addEventListener('click', () => initiateCheckout(cart));
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && els.drawer.classList.contains('open')) {
                closeCart();
            }
        });

        updateCartUI();
        console.log('[CART] Ready. Items:', cart.length);
    }
})();
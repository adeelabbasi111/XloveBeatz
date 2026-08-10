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
            discountRow: $('discountRow'),
            cartDiscount: $('cartDiscount'),
            discountLabel: $('discountLabel'),
            offerDiscountRow: $('offerDiscountRow'),
            cartOfferDiscount: $('cartOfferDiscount'),
            offerSavingsSection: $('offerSavingsSection'),
            offerSavingsRows: $('offerSavingsRows'),
            cartCount: $('cartCount'),
            itemsCount: $('cartItemsCount'),
            checkoutBtn: $('checkoutBtn'),
            emptyState: $('emptyCartState'),
            suggestions: $('cartSuggestions'),
            footer: $('cartFooter'),
            toastContainer: $('toastContainer'),
            couponSection: $('couponSection'),
            couponToggle: $('couponToggle'),
            couponBody: $('couponBody'),
            couponInputWrap: $('couponInputWrap'),
            couponInput: $('couponInput'),
            couponApplyBtn: $('couponApplyBtn'),
            couponApplied: $('couponApplied'),
            couponAppliedCode: $('couponAppliedCode'),
            couponAppliedDesc: $('couponAppliedDesc'),
            couponRemoveBtn: $('couponRemoveBtn'),
            couponError: $('couponError')
        };

        if (!els.drawer) { console.error('[CART] #cartDrawer missing'); return; }
        if (!els.openBtn) { console.error('[CART] #openCartBtn missing'); return; }

        let cart = [];
        let pendingCheckoutItems = null;
        let isProcessing = false;
        let offerDiscountCents = 0;
        let offerBlocksCoupons = false;

        // Coupon state
        let appliedCoupon = null;

        try {
            const raw = localStorage.getItem('xlovebeats_cart');
            cart = raw ? JSON.parse(raw) : [];
            if (!Array.isArray(cart)) cart = [];
        } catch (e) { cart = []; }

        try {
            const rawCoupon = sessionStorage.getItem('xlovebeats_coupon');
            if (rawCoupon) {
                appliedCoupon = JSON.parse(rawCoupon);
            }
        } catch (e) {}

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

        const saveCoupon = () => {
            try {
                if (appliedCoupon) {
                    sessionStorage.setItem('xlovebeats_coupon', JSON.stringify(appliedCoupon));
                } else {
                    sessionStorage.removeItem('xlovebeats_coupon');
                }
            } catch (e) {}
        };

        function showToast(message, type) {
            type = type || 'success';
            if (!els.toastContainer) return;
            var icons = {
                success: 'fa-check',
                error: 'fa-exclamation-circle',
                info: 'fa-info-circle',
                warning: 'fa-exclamation-triangle'
            };
            var toast = document.createElement('div');
            toast.className = 'toast toast-' + type;
            toast.innerHTML =
                '<div class="toast-icon"><i class="fas ' + (icons[type] || icons.success) + '"></i></div>' +
                '<span>' + message + '</span>';
            els.toastContainer.appendChild(toast);
            setTimeout(function() {
                toast.classList.add('toast-out');
                toast.addEventListener('animationend', function() { toast.remove(); }, { once: true });
            }, 2800);
        }

        function popBadge() {
            if (!els.cartCount) return;
            els.cartCount.classList.remove('badge-pop');
            void els.cartCount.offsetWidth;
            els.cartCount.classList.add('badge-pop');
            setTimeout(function() { els.cartCount.classList.remove('badge-pop'); }, 500);
        }

        function escapeHtml(text) {
            var div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function renderEmptyState() {
            if (!els.itemsList) return;
            els.itemsList.innerHTML = '';
            var empty = document.createElement('div');
            empty.className = 'empty-cart-state';
            empty.id = 'emptyCartState';
            empty.innerHTML =
                '<div class="empty-cart-vinyl">' +
                    '<div class="empty-vinyl-grooves"></div>' +
                    '<i class="fas fa-music"></i>' +
                '</div>' +
                '<p class="empty-cart-title">Your cart is empty</p>' +
                '<p class="empty-cart-subtitle">Drop some fire beats in here 🔥</p>' +
                '<button class="empty-cart-cta" id="browseBeatsBtn">Browse Beats</button>';
            els.itemsList.appendChild(empty);
            var btn = empty.querySelector('#browseBeatsBtn');
            if (btn) {
                btn.addEventListener('click', function() {
                    closeCart();
                    setTimeout(function() {
                        var tab = document.querySelector('[data-tab="beat-packs"]');
                        if (tab) tab.click();
                        var section = document.getElementById('beat-packs');
                        if (section) section.scrollIntoView({ behavior: 'smooth' });
                    }, 300);
                });
            }
        }

        // Coupon UI helpers
        function showCouponInput() {
            if (els.couponInputWrap) els.couponInputWrap.style.display = 'flex';
            if (els.couponApplied) els.couponApplied.style.display = 'none';
            if (els.couponError) els.couponError.style.display = 'none';
            if (els.couponInput) {
                els.couponInput.value = '';
                els.couponInput.focus();
            }
        }

        function showCouponApplied() {
            if (!appliedCoupon) return;
            if (els.couponInputWrap) els.couponInputWrap.style.display = 'none';
            if (els.couponError) els.couponError.style.display = 'none';
            if (els.couponApplied) {
                els.couponApplied.style.display = 'flex';
                if (els.couponAppliedCode) els.couponAppliedCode.textContent = appliedCoupon.code;
                if (els.couponAppliedDesc) els.couponAppliedDesc.textContent = appliedCoupon.description || '';
            }
        }

        function showCouponError(msg) {
            if (els.couponError) {
                els.couponError.textContent = msg;
                els.couponError.style.display = 'block';
            }
            if (els.couponInput) {
                els.couponInput.classList.add('coupon-input-error');
                setTimeout(function() { if (els.couponInput) els.couponInput.classList.remove('coupon-input-error'); }, 600);
            }
        }

        function updateCouponUI() {
            if (appliedCoupon) {
                showCouponApplied();
            } else {
                showCouponInput();
            }
        }

        // Calculate discount
        function calculateDiscount(subtotal) {
            if (!appliedCoupon || subtotal <= 0) return 0;
            if (appliedCoupon.discount_type === 'percentage') {
                var raw = subtotal * (appliedCoupon.discount_value / 100);
                var max = appliedCoupon.max_discount ? appliedCoupon.max_discount : Infinity;
                return Math.min(raw, max);
            } else if (appliedCoupon.discount_type === 'fixed') {
                return Math.min(appliedCoupon.discount_value, subtotal);
            }
            return 0;
        }

        async function updateCartUI() {
            if (!els.itemsList) return;

            var count = cart.length;
            var subtotal = cart.reduce(function(sum, item) { return sum + (parseFloat(item.price) || 0); }, 0);
            var couponDiscount = calculateDiscount(subtotal);
            var offerDiscount = offerDiscountCents / 100;
            var total = Math.max(0, subtotal - couponDiscount - offerDiscount);

            if (els.cartCount) {
                var old = parseInt(els.cartCount.textContent) || 0;
                els.cartCount.textContent = count;
                if (count > old) popBadge();
            }

            var mobileBadge = document.getElementById('mobileCartCount');
            if (mobileBadge) {
                if (count > 0) {
                    mobileBadge.textContent = count > 9 ? '9+' : count;
                    mobileBadge.style.display = 'flex';
                } else {
                    mobileBadge.style.display = 'none';
                }
            }

            if (els.itemsCount) els.itemsCount.textContent = count + ' item' + (count !== 1 ? 's' : '');

            if (count === 0) {
                renderEmptyState();
                if (els.checkoutBtn) els.checkoutBtn.disabled = true;
                if (els.subtotal) els.subtotal.textContent = formatPrice(0);
                if (els.grandTotal) els.grandTotal.textContent = formatPrice(0);
                if (els.discountRow) els.discountRow.style.display = 'none';
                if (els.offerDiscountRow) els.offerDiscountRow.style.display = 'none';
                if (els.footer) els.footer.style.opacity = '0.6';
                if (els.suggestions) els.suggestions.style.display = 'block';
                if (els.couponSection) els.couponSection.style.display = 'none';
                offerDiscountCents = 0;
                offerBlocksCoupons = false;
                if (appliedCoupon) {
                    appliedCoupon = null;
                    saveCoupon();
                    updateCouponUI();
                }
                saveCart();
                return;
            }

            if (els.suggestions) els.suggestions.style.display = 'none';
            if (els.footer) els.footer.style.opacity = '1';
            if (els.checkoutBtn) els.checkoutBtn.disabled = false;

            els.itemsList.innerHTML = '';
            cart.forEach(function(item, index) {
                var cfg = {
                    pack: { cls: 'pack', label: 'Pack', icon: 'fa-compact-disc' },
                    preset: { cls: 'preset', label: 'Preset', icon: 'fa-microphone-alt' },
                    single: { cls: 'single', label: 'Single', icon: 'fa-music' }
                }[item.type] || { cls: 'single', label: 'Single', icon: 'fa-music' };

                var div = document.createElement('div');
                div.className = 'cart-item';
                div.style.animationDelay = (index * 0.06) + 's';
                div.innerHTML =
                    '<div class="cart-item-thumb">' +
                        (item.image ? '<img src="' + item.image + '" alt="" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">' : '') +
                        '<div class="thumb-placeholder"' + (item.image ? ' style="display:none"' : '') + '>' +
                            '<i class="fas ' + cfg.icon + '"></i>' +
                        '</div>' +
                    '</div>' +
                    '<div class="cart-item-info">' +
                        '<div class="cart-item-name">' + escapeHtml(item.name) + '</div>' +
                        '<div class="cart-item-meta">' +
                            '<span class="cart-item-type ' + cfg.cls + '">' + cfg.label + '</span>' +
                            (item.license ? '<span class="cart-item-license">' + escapeHtml(item.license) + ' License</span>' : '') +
                        '</div>' +
                    '</div>' +
                    '<div class="cart-item-right">' +
                        '<div class="cart-item-price">' + formatPrice(item.price) + '</div>' +
                        '<button class="remove-item" data-index="' + index + '" title="Remove">' +
                            '<i class="fas fa-trash"></i>' +
                        '</button>' +
                    '</div>';
                els.itemsList.appendChild(div);
            });

            if (els.subtotal) els.subtotal.textContent = formatPrice(subtotal);

            if (couponDiscount > 0) {
                if (els.discountRow) els.discountRow.style.display = 'flex';
                if (els.cartDiscount) els.cartDiscount.textContent = '-' + formatPrice(couponDiscount);
                if (els.discountLabel && appliedCoupon) {
                    els.discountLabel.textContent = '(' + appliedCoupon.code + ')';
                }
            } else {
                if (els.discountRow) els.discountRow.style.display = 'none';
            }

            if (offerDiscount > 0) {
                if (els.offerDiscountRow) els.offerDiscountRow.style.display = 'flex';
                if (els.cartOfferDiscount) els.cartOfferDiscount.textContent = '-' + formatPrice(offerDiscount);
            } else {
                if (els.offerDiscountRow) els.offerDiscountRow.style.display = 'none';
            }

            if (els.grandTotal) els.grandTotal.textContent = formatPrice(total);

            if (offerBlocksCoupons && offerDiscount > 0) {
                if (els.couponSection) {
                    els.couponSection.style.display = 'block';
                    var existingNotice = els.couponSection.querySelector('.offer-blocks-notice');
                    if (!existingNotice) {
                        var notice = document.createElement('div');
                        notice.className = 'offer-blocks-notice';
                        notice.style.cssText = 'padding:10px 14px;background:rgba(251,146,60,0.12);border:1px solid rgba(251,146,60,0.3);border-radius:8px;color:#fb923c;font-size:0.82rem;margin-top:8px;';
                        notice.innerHTML = '<i class="fas fa-info-circle" style="margin-right:6px;"></i>Coupon codes cannot be used with the active offer.';
                        els.couponSection.appendChild(notice);
                    }
                    if (els.couponBody) els.couponBody.style.display = 'none';
                    if (els.couponToggle) els.couponToggle.style.pointerEvents = 'none';
                }
            } else {
                if (els.couponSection) els.couponSection.style.display = 'block';
                var notice2 = els.couponSection && els.couponSection.querySelector('.offer-blocks-notice');
                if (notice2) notice2.remove();
                if (els.couponToggle) els.couponToggle.style.pointerEvents = '';
            }

            saveCart();

            // Async fetch offer discounts
            if (count > 0) {
                try {
                    var resp = await fetch("/api/cart/offer-check", {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": window.CSRF_TOKEN || ""
                        },
                        body: JSON.stringify({
                            items: cart.map(function(item) {
                                return {
                                    id: item.id,
                                    type: item.type === "single" ? "beat" : item.type,
                                    price: parseFloat(item.price) || 0,
                                    license: item.license
                                };
                            })
                        })
                    });

                    if (resp.ok) {
                        var data = await resp.json();
                        var newOfferCents = data.discount_cents || 0;
                        offerBlocksCoupons = !!data.blocks_coupons;

                        if (newOfferCents !== offerDiscountCents) {
                            offerDiscountCents = newOfferCents;
                            var offerRupees = offerDiscountCents / 100;
                            var newTotal = Math.max(0, subtotal - couponDiscount - offerRupees);

                            if (els.offerDiscountRow) els.offerDiscountRow.style.display = offerRupees > 0 ? 'flex' : 'none';
                            if (els.cartOfferDiscount && offerRupees > 0) els.cartOfferDiscount.textContent = '-' + formatPrice(offerRupees);
                            if (els.grandTotal) els.grandTotal.textContent = formatPrice(newTotal);

                            if (els.offerSavingsSection && data.offer_summary && data.offer_summary.length > 0) {
                                els.offerSavingsSection.style.display = 'block';
                                if (els.offerSavingsRows) {
                                    els.offerSavingsRows.innerHTML = data.offer_summary.map(function(s) {
                                        return '<div style="display:flex;justify-content:space-between;font-size:0.8rem;padding:4px 8px;background:rgba(52,211,153,0.08);border-radius:6px;margin-bottom:4px;color:#34d399">' +
                                            '<span>' + escapeHtml(s.label) + '</span>' +
                                            '<span>-₹' + (s.saving_cents / 100).toFixed(0) + '</span>' +
                                        '</div>';
                                    }).join('');
                                }
                            } else if (els.offerSavingsSection) {
                                els.offerSavingsSection.style.display = 'none';
                            }

                            if (offerBlocksCoupons && offerRupees > 0) {
                                if (els.couponBody) els.couponBody.style.display = 'none';
                                if (els.couponToggle) els.couponToggle.style.pointerEvents = 'none';
                                var existingNotice2 = els.couponSection && els.couponSection.querySelector('.offer-blocks-notice');
                                if (!existingNotice2 && els.couponSection) {
                                    var notice3 = document.createElement('div');
                                    notice3.className = 'offer-blocks-notice';
                                    notice3.style.cssText = 'padding:10px 14px;background:rgba(251,146,60,0.12);border:1px solid rgba(251,146,60,0.3);border-radius:8px;color:#fb923c;font-size:0.82rem;margin-top:8px;';
                                    notice3.innerHTML = '<i class="fas fa-info-circle" style="margin-right:6px;"></i>Coupon codes cannot be used with the active offer.';
                                    els.couponSection.appendChild(notice3);
                                }
                            } else {
                                if (els.couponToggle) els.couponToggle.style.pointerEvents = '';
                                var notice4 = els.couponSection && els.couponSection.querySelector('.offer-blocks-notice');
                                if (notice4) notice4.remove();
                            }
                        }
                    }
                } catch (e) { /* silent fail */ }
            }
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
            var exists = cart.find(function(i) { return i.id === item.id && i.license === item.license; });
            if (exists) {
                showToast('⚠️ Already in cart', 'warning');
                openCart();
                return;
            }
            cart.push(item);
            showToast('🛒 ' + item.name + ' added to cart!', 'success');
            updateCartUI();
            openCart();
        }

        function removeItem(index) {
            var items = els.itemsList.querySelectorAll('.cart-item');
            if (items[index]) {
                items[index].classList.add('removing');
                items[index].addEventListener('animationend', function() {
                    cart.splice(index, 1);
                    updateCartUI();
                }, { once: true });
            } else {
                cart.splice(index, 1);
                updateCartUI();
            }
        }

        // Coupon Actions
        async function applyCoupon() {
            if (!els.couponInput) return;
            var code = els.couponInput.value.trim();
            if (!code) {
                showCouponError('Please enter a coupon code');
                return;
            }

            var applyText = els.couponApplyBtn.querySelector('.coupon-apply-text');
            var applySpin = els.couponApplyBtn.querySelector('.fa-spinner');
            if (applyText) applyText.style.display = 'none';
            if (applySpin) applySpin.style.display = 'inline-block';
            if (els.couponApplyBtn) els.couponApplyBtn.disabled = true;
            if (els.couponError) els.couponError.style.display = 'none';

            try {
                var subtotal = cart.reduce(function(sum, item) { return sum + (parseFloat(item.price) || 0); }, 0);
                var res = await fetch('/api/validate-coupon', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.CSRF_TOKEN || ''
                    },
                    body: JSON.stringify({ code: code, subtotal: subtotal })
                });

                var data = await res.json();

                if (data.valid) {
                    appliedCoupon = {
                        code: data.code,
                        discount_type: data.discount_type,
                        discount_value: data.discount_value,
                        max_discount: data.max_discount || null,
                        description: data.description || ''
                    };
                    saveCoupon();
                    showToast('🎉 Coupon "' + data.code + '" applied!', 'success');
                    showCouponApplied();
                    updateCartUI();
                } else {
                    showCouponError(data.error || 'Invalid coupon code');
                }
            } catch (err) {
                showCouponError('Failed to validate coupon. Try again.');
            } finally {
                if (applyText) applyText.style.display = 'inline';
                if (applySpin) applySpin.style.display = 'none';
                if (els.couponApplyBtn) els.couponApplyBtn.disabled = false;
            }
        }

        function removeCoupon() {
            appliedCoupon = null;
            saveCoupon();
            showToast('Coupon removed', 'info');
            showCouponInput();
            updateCartUI();
        }

        window.addToGlobalCart = function(item, isBuyNow) {
            isBuyNow = isBuyNow || false;
            addItem(item);
            if (isBuyNow) {
                setTimeout(function() {
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
            appliedCoupon = null;
            saveCoupon();
            updateCartUI();
            showToast('Cart cleared', 'info');
        };

        async function checkIfUserLoggedIn() {
            try {
                var res = await fetch('/api/auth/me');
                var data = await res.json();
                return data.logged_in || false;
            } catch (err) { return false; }
        }

        function showLoginModal() {
            var modal = $('loginModal');
            if (!modal) return;
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
            var sub = modal.querySelector('.auth-modal-header p');
            if (sub) {
                if (!sub.dataset.originalText) sub.dataset.originalText = sub.textContent;
                sub.textContent = 'Please login to complete your purchase';
                sub.style.color = 'var(--accent-soft)';
            }
        }

        function restoreLoginModal() {
            var modal = $('loginModal');
            if (!modal) return;
            var sub = modal.querySelector('.auth-modal-header p');
            if (sub && sub.dataset.originalText) {
                sub.textContent = sub.dataset.originalText;
                sub.style.color = '';
            }
        }

        async function initiateCheckout(itemsToCheckout) {
            if (!itemsToCheckout || itemsToCheckout.length === 0 || isProcessing) return;
            isProcessing = true;

            var isLoggedIn = await checkIfUserLoggedIn();
            if (!isLoggedIn) {
                closeCart();
                pendingCheckoutItems = itemsToCheckout;
                showLoginModal();
                showToast('🔐 Login required to checkout', 'warning');
                isProcessing = false;
                return;
            }

            // Handle exclusive items first (WhatsApp redirect for both regions)
            var exclusiveItems = itemsToCheckout.filter(function(i) { return i.license === 'exclusive'; });
            if (exclusiveItems.length > 0) {
                var names = exclusiveItems.map(function(i) { return i.name; }).join(', ');
                var msg = 'Hello, I am interested in buying the Exclusive License for: ' + names + '. Please let me know the price.';
                window.open('https://wa.me/918329189796?text=' + encodeURIComponent(msg), '_blank');
                showToast('📱 Redirecting to WhatsApp...', 'info');
                exclusiveItems.forEach(function(item) {
                    var idx = cart.findIndex(function(i) { return i.id === item.id && i.license === item.license; });
                    if (idx > -1) cart.splice(idx, 1);
                });
                updateCartUI();
                closeCart();
                isProcessing = false;
                return;
            }

            // Proceed directly to Cashfree checkout
            await proceedWithPayment(itemsToCheckout);
            isProcessing = false;
        }

        async function proceedWithPayment(itemsToCheckout) {

            var origHTML = els.checkoutBtn ? els.checkoutBtn.innerHTML : '';
            if (els.checkoutBtn) {
                els.checkoutBtn.innerHTML = '<span class="checkout-btn-content"><i class="fas fa-spinner fa-spin"></i><span>Processing...</span></span>';
                els.checkoutBtn.disabled = true;
            }

            try {
                var res = await fetch('/api/create-payu-order', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.CSRF_TOKEN || ''
                    },
                    body: JSON.stringify({
                        items: itemsToCheckout,
                        coupon_code: appliedCoupon ? appliedCoupon.code : null
                    })
                });

                var orderData = await res.json();
                if (orderData.error) throw new Error(orderData.error);

                // --- TEST MODE BYPASS ---
                if (orderData.test_mode_success) {
                    showToast('✅ Test Payment Successful! Redirecting...', 'success');
                    
                    // Clear cart items that were checked out
                    itemsToCheckout.forEach(function(item) {
                        var idx = cart.findIndex(function(i) { return i.id === item.id && i.license === item.license; });
                        if (idx > -1) cart.splice(idx, 1);
                    });
                    
                    appliedCoupon = null;
                    saveCoupon();
                    updateCartUI();
                    closeCart();
                    
                    window.location.href = '/payment/success/' + orderData.db_order_id;
                    return;
                }
                // -------------------------

                if (els.checkoutBtn) {
                    els.checkoutBtn.innerHTML = '<span class="checkout-btn-content"><i class="fas fa-spinner fa-spin"></i><span>Redirecting to PayU...</span></span>';
                }

                // Dynamically create PayU form and submit
                var form = document.createElement("form");
                form.setAttribute("method", "POST");
                form.setAttribute("action", orderData.action);

                var fields = {
                    "key": orderData.key,
                    "txnid": orderData.txnid,
                    "amount": orderData.amount,
                    "productinfo": orderData.productinfo,
                    "firstname": orderData.firstname,
                    "email": orderData.email,
                    "phone": orderData.phone,
                    "surl": orderData.surl,
                    "furl": orderData.furl,
                    "hash": orderData.hash
                };

                for (var key in fields) {
                    if (fields.hasOwnProperty(key)) {
                        var hiddenField = document.createElement("input");
                        hiddenField.setAttribute("type", "hidden");
                        hiddenField.setAttribute("name", key);
                        hiddenField.setAttribute("value", fields[key]);
                        form.appendChild(hiddenField);
                    }
                }

                document.body.appendChild(form);
                form.submit();

            } catch (err) {
                console.error(err);
                showToast('❌ ' + err.message, 'error');
                if (els.checkoutBtn) {
                    els.checkoutBtn.innerHTML = origHTML;
                    els.checkoutBtn.disabled = false;
                }
            }
        }

        window.resumeCheckoutAfterLogin = async function() {
            if (!pendingCheckoutItems || pendingCheckoutItems.length === 0) return;
            restoreLoginModal();
            var items = pendingCheckoutItems;
            pendingCheckoutItems = null;

            setTimeout(async function() {
                var isLoggedIn = await checkIfUserLoggedIn();
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
        els.openBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            openCart();
        });

        var mobileCartBtn = document.getElementById('mobileCartBtn');
        if (mobileCartBtn) {
            mobileCartBtn.addEventListener('click', function(e) {
                e.preventDefault();
                openCart();
            });
        }

        if (els.closeBtn) {
            els.closeBtn.addEventListener('click', function(e) {
                e.preventDefault();
                closeCart();
            });
        }

        if (els.overlay) els.overlay.addEventListener('click', closeCart);

        if (els.itemsList) {
            els.itemsList.addEventListener('click', function(e) {
                var btn = e.target.closest('.remove-item');
                if (btn) {
                    var idx = parseInt(btn.dataset.index);
                    if (!isNaN(idx)) removeItem(idx);
                }
            });
        }

        if (els.checkoutBtn) {
            els.checkoutBtn.addEventListener('click', function() { initiateCheckout(cart); });
        }

        // Coupon events
        if (els.couponToggle) {
            els.couponToggle.addEventListener('click', function() {
                var body = els.couponBody;
                if (!body) return;
                var isOpen = body.style.display !== 'none';
                body.style.display = isOpen ? 'none' : 'block';
                els.couponToggle.classList.toggle('coupon-toggle-open', !isOpen);
            });
        }

        if (els.couponApplyBtn) {
            els.couponApplyBtn.addEventListener('click', applyCoupon);
        }

        if (els.couponInput) {
            els.couponInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    applyCoupon();
                }
            });
        }

        if (els.couponRemoveBtn) {
            els.couponRemoveBtn.addEventListener('click', removeCoupon);
        }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                if (els.drawer.classList.contains('open')) {
                    closeCart();
                }
            }
        });

        // Initial state
        updateCouponUI();
        updateCartUI();
        console.log('[CART] Ready. Items:', cart.length);
    }
})();
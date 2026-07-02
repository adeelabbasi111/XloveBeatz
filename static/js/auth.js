(function() {
    'use strict';

    // ==================== ELEMENTS ====================
    var loginModal = document.getElementById('loginModal');
    var signupModal = document.getElementById('signupModal');
    var openLoginBtn = document.getElementById('openLoginBtn');
    var openSignupBtn = document.getElementById('openSignupBtn');
    var closeLoginBtn = document.getElementById('closeLoginBtn');
    var closeSignupBtn = document.getElementById('closeSignupBtn');
    var switchToSignup = document.getElementById('switchToSignup');
    var switchToLogin = document.getElementById('switchToLogin');
    var loginForm = document.getElementById('loginForm');
    var signupForm = document.getElementById('signupForm');
    var loginError = document.getElementById('loginError');
    var signupError = document.getElementById('signupError');

    var userSidebar = document.getElementById('userSidebar');
    var userSidebarOverlay = document.getElementById('userSidebarOverlay');
    var openUserSidebarBtn = document.getElementById('openUserSidebarBtn');
    var closeUserSidebarBtn = document.getElementById('closeUserSidebarBtn');

    var guestAuthBtns = document.getElementById('guestAuthBtns');
    var userMenuBtns = document.getElementById('userMenuBtns');
    var headerUsername = document.getElementById('headerUsername');
    var header = document.getElementById('header');

    var accountBtn = document.getElementById('accountBtn');
    var mobileAccountBtn = document.getElementById('mobileAccountBtn');
    var accountModal = document.getElementById('accountModal');
    var accountModalOverlay = document.getElementById('accountModalOverlay');
    var closeAccountModalBtn = document.getElementById('closeAccountModalBtn');
    var accountTabBtns = document.querySelectorAll('.account-tab-btn[data-atab]');
    var accountTabContents = document.querySelectorAll('.account-tab-content');

    var mobileNavItems = document.querySelectorAll('.mobile-nav-item');

    // ==================== STATE ====================
    var currentUser = null;

    // ==================== MODAL CONTROLS ====================
    function openModal(modal) {
        if (!modal) return;
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeModal(modal) {
        if (!modal) return;
        modal.classList.remove('active');
        document.body.style.overflow = '';
        if (modal === loginModal) {
            if (loginForm) loginForm.reset();
            if (loginError) loginError.classList.remove('show');
        } else if (modal === signupModal) {
            if (signupForm) signupForm.reset();
            if (signupError) signupError.classList.remove('show');
        }
    }

    function openAccountModal() {
        if (!accountModal || !accountModalOverlay) return;
        accountModalOverlay.classList.add('active');
        setTimeout(function() { accountModal.classList.add('open'); }, 10);
        document.body.style.overflow = 'hidden';

        // Load real data when opening
        if (currentUser) {
            loadAccountProducts();
            loadAccountLicenses();
            loadAccountProfile();
        }
    }

    function closeAccountModal() {
        if (!accountModal || !accountModalOverlay) return;
        accountModal.classList.remove('open');
        setTimeout(function() {
            accountModalOverlay.classList.remove('active');
            document.body.style.overflow = '';
        }, 350);
    }

    if (openLoginBtn) openLoginBtn.addEventListener('click', function() { openModal(loginModal); });
    if (openSignupBtn) openSignupBtn.addEventListener('click', function() { openModal(signupModal); });
    if (closeLoginBtn) closeLoginBtn.addEventListener('click', function() { closeModal(loginModal); });
    if (closeSignupBtn) closeSignupBtn.addEventListener('click', function() { closeModal(signupModal); });

    if (closeAccountModalBtn) closeAccountModalBtn.addEventListener('click', closeAccountModal);
    if (accountModalOverlay) {
        accountModalOverlay.addEventListener('click', function(e) {
            if (e.target === accountModalOverlay) closeAccountModal();
        });
    }

    if (switchToSignup) switchToSignup.addEventListener('click', function(e) {
        e.preventDefault();
        closeModal(loginModal);
        setTimeout(function() { openModal(signupModal); }, 200);
    });

    if (switchToLogin) switchToLogin.addEventListener('click', function(e) {
        e.preventDefault();
        closeModal(signupModal);
        setTimeout(function() { openModal(loginModal); }, 200);
    });

    [loginModal, signupModal].forEach(function(modal) {
        if (modal) modal.addEventListener('click', function(e) {
            if (e.target === modal) closeModal(modal);
        });
    });

    // ==================== SIDEBAR CONTROLS ====================
    function openUserSidebar() {
        if (!userSidebar) return;
        userSidebar.classList.add('open');
        if (userSidebarOverlay) userSidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        loadUserPurchases();
    }

    function closeUserSidebar() {
        if (!userSidebar) return;
        userSidebar.classList.remove('open');
        if (userSidebarOverlay) userSidebarOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (openUserSidebarBtn) openUserSidebarBtn.addEventListener('click', openUserSidebar);
    if (closeUserSidebarBtn) closeUserSidebarBtn.addEventListener('click', closeUserSidebar);
    if (userSidebarOverlay) userSidebarOverlay.addEventListener('click', closeUserSidebar);

    // Sidebar Tabs
    var userTabBtns = document.querySelectorAll('.user-tab-btn');
    var userTabContents = document.querySelectorAll('.user-tab-content');
    userTabBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            var target = btn.dataset.utab;
            userTabBtns.forEach(function(b) { b.classList.remove('active'); });
            userTabContents.forEach(function(c) { c.classList.remove('active'); });
            btn.classList.add('active');
            var tabContent = document.getElementById('utab-' + target);
            if (tabContent) tabContent.classList.add('active');
        });
    });

    // Account Modal Tabs
    function activateAccountTab(tabId) {
        accountTabContents.forEach(function(c) { c.classList.remove('active'); });
        var activeContent = document.getElementById('atab-' + tabId);
        if (activeContent) activeContent.classList.add('active');
        accountTabBtns.forEach(function(btn) {
            btn.classList.toggle('active', btn.dataset.atab === tabId);
        });
    }

    accountTabBtns.forEach(function(btn) {
        btn.addEventListener('click', function() { activateAccountTab(btn.dataset.atab); });
    });

    // ==================== AUTH UI STATE ====================
    function updateAuthUI(user) {
        currentUser = user;
        var isLoggedIn = !!user;

        if (guestAuthBtns) guestAuthBtns.style.display = isLoggedIn ? 'none' : 'flex';
        if (userMenuBtns) userMenuBtns.style.display = isLoggedIn ? 'flex' : 'none';
        if (headerUsername && user) headerUsername.textContent = user.username;

        if (accountBtn) accountBtn.classList.toggle('logged-in', isLoggedIn);
        if (mobileAccountBtn) mobileAccountBtn.classList.toggle('logged-in', isLoggedIn);

        var avatar = document.getElementById('accountAvatar');
        var modalUsername = document.getElementById('accountModalUsername');
        var modalEmail = document.getElementById('accountModalEmail');

        if (isLoggedIn && user) {
            if (modalUsername) modalUsername.textContent = user.username || 'User';
            if (modalEmail) modalEmail.textContent = user.email || 'Member';
            if (avatar) {
                avatar.innerHTML = '<span style="font-weight:800;font-size:1.2rem;">' +
                    (user.username ? user.username.charAt(0).toUpperCase() : 'U') + '</span>';
            }
        } else {
            if (modalUsername) modalUsername.textContent = 'Guest';
            if (modalEmail) modalEmail.textContent = 'Sign in to access your account';
            if (avatar) avatar.innerHTML = '<i class="fas fa-user-circle"></i>';
        }

        // Settings
        var settingsLoggedIn = document.getElementById('settingsLoggedIn');
        var settingsGuest = document.getElementById('settingsGuest');
        var settingsUsername = document.getElementById('settingsUsername');
        var settingsEmail = document.getElementById('settingsEmail');
        var settingsJoined = document.getElementById('settingsJoined');

        if (isLoggedIn && user) {
            if (settingsLoggedIn) settingsLoggedIn.style.display = 'block';
            if (settingsGuest) settingsGuest.style.display = 'none';
            if (settingsUsername) settingsUsername.textContent = user.username || '-';
            if (settingsEmail) settingsEmail.textContent = user.email || '-';
            if (settingsJoined) settingsJoined.textContent = user.joined || '-';
        } else {
            if (settingsLoggedIn) settingsLoggedIn.style.display = 'none';
            if (settingsGuest) settingsGuest.style.display = 'block';
        }

        // Products & Licenses Guest States
        var productsGuestState = document.getElementById('productsGuestState');
        var licensesGuestState = document.getElementById('licensesGuestState');
        var productsList = document.getElementById('productsList');
        var licensesList = document.getElementById('licensesList');

        if (isLoggedIn) {
            if (productsGuestState) productsGuestState.style.display = 'none';
            if (licensesGuestState) licensesGuestState.style.display = 'none';
            if (productsList) productsList.style.display = 'block';
            if (licensesList) licensesList.style.display = 'block';
        } else {
            if (productsGuestState) productsGuestState.style.display = 'block';
            if (licensesGuestState) licensesGuestState.style.display = 'block';
            if (productsList) productsList.style.display = 'none';
            if (licensesList) licensesList.style.display = 'none';
        }

        if (!isLoggedIn) {
            closeUserSidebar();
            closeAccountModal();
        }
    }

    // ==================== LOAD ACCOUNT PRODUCTS ====================
    async function loadAccountProducts() {
        var list = document.getElementById('productsList');
        var count = document.getElementById('productCount');
        if (!list) return;

        list.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i><p>Loading your products...</p></div>';

        try {
            var res = await fetch('/api/user/purchases');
            var data = await res.json();

            if (data.error) {
                list.innerHTML = '<div class="empty-state"><i class="fas fa-lock"></i><p>' + data.error + '</p></div>';
                return;
            }

            var purchases = data.purchases || [];
            if (count) count.textContent = purchases.length + ' item' + (purchases.length !== 1 ? 's' : '');

            if (purchases.length === 0) {
                list.innerHTML = '<div class="empty-state"><i class="fas fa-shopping-bag"></i><p>No purchases yet</p><p style="font-size:0.8rem;margin-top:6px;opacity:0.6;">Start exploring our beats!</p></div>';
                return;
            }

            var typeIcons = { beat: 'fa-music', pack: 'fa-layer-group', preset: 'fa-sliders-h' };
            var licenseColors = { Basic: 'var(--accent-soft)', Premium: '#3b82f6', Exclusive: '#C9AE74', Standard: 'var(--text-muted)' };

            list.innerHTML = purchases.map(function(p) {
                var icon = typeIcons[p.product_type] || 'fa-box';
                var licColor = licenseColors[p.license] || 'var(--accent-soft)';
                return '<div class="product-item">' +
                    '<div class="product-item-header">' +
                        '<div>' +
                            '<div class="product-item-name"><i class="fas ' + icon + '" style="margin-right:8px;opacity:0.5;font-size:0.8rem;"></i>' + p.product_name + '</div>' +
                            '<div class="product-item-type">' + p.product_type + ' &bull; ' + p.order_date + '</div>' +
                        '</div>' +
                        '<span class="product-item-license" style="background:' + licColor + '20;color:' + licColor + ';">' + p.license + '</span>' +
                    '</div>' +
                    '<div class="product-item-footer">' +
                        '<span>₹' + p.price_paid.toFixed(0) + ' &bull; ' + p.download_count + ' downloads</span>' +
                        '<a href="/download/' + p.product_id + '" class="product-download-btn"><i class="fas fa-download"></i> Download</a>' +
                    '</div>' +
                '</div>';
            }).join('');

        } catch (err) {
            list.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-circle"></i><p>Failed to load products</p></div>';
        }
    }

    // ==================== LOAD ACCOUNT LICENSES ====================
    async function loadAccountLicenses() {
        var list = document.getElementById('licensesList');
        var count = document.getElementById('licenseCount');
        if (!list) return;

        list.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i><p>Loading your licenses...</p></div>';

        try {
            var res = await fetch('/api/user/licenses');
            var data = await res.json();

            if (data.error) {
                list.innerHTML = '<div class="empty-state"><i class="fas fa-lock"></i><p>' + data.error + '</p></div>';
                return;
            }

            var licenses = data.licenses || [];
            if (count) count.textContent = licenses.length + ' item' + (licenses.length !== 1 ? 's' : '');

            if (licenses.length === 0) {
                list.innerHTML = '<div class="empty-state"><i class="fas fa-file-contract"></i><p>No licenses yet</p><p style="font-size:0.8rem;margin-top:6px;opacity:0.6;">Licenses are generated after purchase</p></div>';
                return;
            }

            list.innerHTML = licenses.map(function(lic) {
                var badgeClass = lic.license_type === 'Exclusive' ? 'gold' : '';
                var downloadBtn = '';
                if (lic.has_pdf) {
                    downloadBtn = '<a href="/download/license/' + lic.license_id + '" class="product-download-btn"><i class="fas fa-file-pdf"></i> Download PDF</a>';
                } else {
                    downloadBtn = '<span style="font-size:0.75rem;color:var(--text-muted);">PDF not available</span>';
                }

                return '<div class="license-item">' +
                    '<div class="license-item-header">' +
                        '<div>' +
                            '<div class="license-item-name">' + lic.product_name + '</div>' +
                            '<div class="license-item-type">' + lic.license_type + ' License &bull; ' + lic.product_type + '</div>' +
                        '</div>' +
                        '<span class="license-item-badge ' + badgeClass + '">' + lic.license_type + '</span>' +
                    '</div>' +
                    '<div class="license-item-footer">' +
                        '<span>Generated ' + lic.generated_at + '</span>' +
                        downloadBtn +
                    '</div>' +
                '</div>';
            }).join('');

        } catch (err) {
            list.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-circle"></i><p>Failed to load licenses</p></div>';
        }
    }

    // ==================== LOAD ACCOUNT PROFILE ====================
    async function loadAccountProfile() {
        try {
            var res = await fetch('/api/user/profile');
            var data = await res.json();

            if (data.error) return;

            var settingsUsername = document.getElementById('settingsUsername');
            var settingsEmail = document.getElementById('settingsEmail');
            var settingsJoined = document.getElementById('settingsJoined');

            if (settingsUsername) settingsUsername.textContent = data.username || '-';
            if (settingsEmail) settingsEmail.textContent = data.email || '-';
            if (settingsJoined) settingsJoined.textContent = data.joined || '-';

            // Pre-fill edit fields
            var editUsername = document.getElementById('editUsername');
            var editEmail = document.getElementById('editEmail');
            if (editUsername) editUsername.value = data.username || '';
            if (editEmail) editEmail.value = data.email || '';

        } catch (err) {
            console.error('Failed to load profile:', err);
        }
    }

    // ==================== EDIT PROFILE ====================
    async function handleProfileSave() {
        var editUsername = document.getElementById('editUsername');
        var editEmail = document.getElementById('editEmail');
        var profileError = document.getElementById('profileError');
        var profileSuccess = document.getElementById('profileSuccess');
        var saveBtn = document.getElementById('saveProfileBtn');

        if (!editUsername || !editEmail) return;

        if (profileError) { profileError.style.display = 'none'; profileError.textContent = ''; }
        if (profileSuccess) { profileSuccess.style.display = 'none'; profileSuccess.textContent = ''; }

        var newUsername = editUsername.value.trim();
        var newEmail = editEmail.value.trim();

        if (!newUsername && !newEmail) {
            if (profileError) {
                profileError.textContent = 'Please fill in at least one field';
                profileError.style.display = 'block';
            }
            return;
        }

        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        }

        try {
            // Get CSRF token from meta tag or cookie
            var csrfToken = '';
            var metaTag = document.querySelector('meta[name="csrf-token"]');
            if (metaTag) {
                csrfToken = metaTag.content;
            }
            // Fallback: try hidden input
            if (!csrfToken) {
                var hiddenCsrf = document.querySelector('input[name="csrf_token"]');
                if (hiddenCsrf) csrfToken = hiddenCsrf.value;
            }

            var headers = { 'Content-Type': 'application/json' };
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            var res = await fetch('/api/user/profile', {
                method: 'PUT',
                headers: headers,
                body: JSON.stringify({ username: newUsername, email: newEmail })
            });
            var data = await res.json();

            if (data.success) {
                if (profileSuccess) {
                    profileSuccess.textContent = data.message || 'Profile updated!';
                    profileSuccess.style.display = 'block';
                }
                showToast('Profile updated successfully', 'success');

                if (data.user) {
                    var settingsUsername = document.getElementById('settingsUsername');
                    var settingsEmail = document.getElementById('settingsEmail');
                    if (settingsUsername) settingsUsername.textContent = data.user.username;
                    if (settingsEmail) settingsEmail.textContent = data.user.email;

                    if (currentUser) {
                        currentUser.username = data.user.username;
                        currentUser.email = data.user.email;
                    }
                    var modalUsername = document.getElementById('accountModalUsername');
                    var modalEmail = document.getElementById('accountModalEmail');
                    if (modalUsername) modalUsername.textContent = data.user.username;
                    if (modalEmail) modalEmail.textContent = data.user.email;
                    if (headerUsername) headerUsername.textContent = data.user.username;
                }
            } else {
                if (profileError) {
                    profileError.textContent = data.error || 'Update failed';
                    profileError.style.display = 'block';
                }
            }
        } catch (err) {
            if (profileError) {
                profileError.textContent = 'Network error. Please try again.';
                profileError.style.display = 'block';
            }
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
            }
        }
        const header = document.querySelector('.site-header');

window.addEventListener('scroll', () => {
    if (window.pageYOffset > 20) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }
});

function bumpCart() {
    const badge = document.getElementById('cartCount');
    badge.classList.remove('bump');
    void badge.offsetWidth;
    badge.classList.add('bump');
}
    }

    // Bind save button
    var saveProfileBtn = document.getElementById('saveProfileBtn');
    if (saveProfileBtn) saveProfileBtn.addEventListener('click', handleProfileSave);

    // ==================== AUTH API CALLS ====================
    async function handleLogin(e) {
        e.preventDefault();
        var formData = new FormData(loginForm);
        var data = {
            email: formData.get('email'),
            password: formData.get('password')
        };

        var submitBtn = document.getElementById('loginSubmitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            var btnText = submitBtn.querySelector('.btn-text');
            var btnLoader = submitBtn.querySelector('.btn-loader');
            if (btnText) btnText.style.display = 'none';
            if (btnLoader) btnLoader.style.display = 'inline';
        }
        if (loginError) loginError.classList.remove('show');

        try {
            var res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            var result = await res.json();

            if (result.success) {
                showToast(result.message, 'success');
                closeModal(loginModal);
                updateAuthUI(result.user);
                if (window.resumeCheckoutAfterLogin) {
                    window.resumeCheckoutAfterLogin();
                }
            } else {
                if (loginError) {
                    loginError.textContent = result.error || 'Login failed';
                    loginError.classList.add('show');
                }
            }
        } catch (err) {
            if (loginError) {
                loginError.textContent = 'Network error. Please try again.';
                loginError.classList.add('show');
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                var btnText = submitBtn.querySelector('.btn-text');
                var btnLoader = submitBtn.querySelector('.btn-loader');
                if (btnText) btnText.style.display = 'inline';
                if (btnLoader) btnLoader.style.display = 'none';
            }
        }
    }

    async function handleSignup(e) {
        e.preventDefault();
        var formData = new FormData(signupForm);
        var data = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            confirm_password: formData.get('confirm_password')
        };

        var submitBtn = document.getElementById('signupSubmitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            var btnText = submitBtn.querySelector('.btn-text');
            var btnLoader = submitBtn.querySelector('.btn-loader');
            if (btnText) btnText.style.display = 'none';
            if (btnLoader) btnLoader.style.display = 'inline';
        }
        if (signupError) signupError.classList.remove('show');

        try {
            var res = await fetch('/api/auth/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            var result = await res.json();

            if (result.success) {
                showToast(result.message, 'success');
                closeModal(signupModal);
                updateAuthUI(result.user);
            } else {
                if (signupError) {
                    signupError.textContent = result.error || 'Signup failed';
                    signupError.classList.add('show');
                }
            }
        } catch (err) {
            if (signupError) {
                signupError.textContent = 'Network error. Please try again.';
                signupError.classList.add('show');
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                var btnText = submitBtn.querySelector('.btn-text');
                var btnLoader = submitBtn.querySelector('.btn-loader');
                if (btnText) btnText.style.display = 'inline';
                if (btnLoader) btnLoader.style.display = 'none';
            }
        }
    }

    async function handleLogout() {
        if (!confirm('Are you sure you want to logout?')) return;

        try {
            var res = await fetch('/api/auth/logout', { method: 'POST' });
            var result = await res.json();
            if (result.success) {
                showToast('Logged out successfully', 'info');
                updateAuthUI(null);
                closeUserSidebar();
                closeAccountModal();
            }
        } catch (err) {
            showToast('Logout failed', 'error');
        }
    }

    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    if (signupForm) signupForm.addEventListener('submit', handleSignup);

    var logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);

    // ==================== ACCOUNT BUTTON CLICK ====================
    function handleAccountClick() {
        openAccountModal();
    }

    if (accountBtn) accountBtn.addEventListener('click', handleAccountClick);
    if (mobileAccountBtn) mobileAccountBtn.addEventListener('click', function(e) {
        e.preventDefault();
        handleAccountClick();
    });

    // Guest buttons
    var guestLoginBtns = ['guestLoginFromProducts', 'guestLoginFromLicenses', 'guestLoginFromSettings'];
    guestLoginBtns.forEach(function(id) {
        var btn = document.getElementById(id);
        if (btn) {
            btn.addEventListener('click', function() {
                closeAccountModal();
                setTimeout(function() { openModal(loginModal); }, 200);
            });
        }
    });

    var guestSignupBtn = document.getElementById('guestSignupFromSettings');
    if (guestSignupBtn) {
        guestSignupBtn.addEventListener('click', function() {
            closeAccountModal();
            setTimeout(function() { openModal(signupModal); }, 200);
        });
    }

    // ==================== SIDEBAR PURCHASES (legacy) ====================
    async function loadUserPurchases() {
        var list = document.getElementById('purchasesList');
        var count = document.getElementById('purchaseCount');
        if (!list) return;

        list.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i><p>Loading your beats...</p></div>';

        try {
            var res = await fetch('/api/user/purchases');
            var data = await res.json();

            if (data.error) {
                list.innerHTML = '<div class="empty-purchases"><i class="fas fa-lock"></i><p>Please login to view purchases</p></div>';
                return;
            }

            var purchases = data.purchases || [];
            if (count) count.textContent = purchases.length + ' item' + (purchases.length !== 1 ? 's' : '');

            if (purchases.length === 0) {
                list.innerHTML = '<div class="empty-purchases"><i class="fas fa-music"></i><p>No purchases yet</p><p style="font-size:0.8rem;margin-top:8px;">Start exploring our beats!</p></div>';
                return;
            }

            list.innerHTML = purchases.map(function(p) {
                return '<div class="purchase-item">' +
                    '<div class="purchase-item-header">' +
                        '<div>' +
                            '<div class="purchase-item-name">' + p.product_name + '</div>' +
                            '<div class="purchase-item-type">' + p.product_type + ' &bull; ' + p.order_date + '</div>' +
                        '</div>' +
                        '<span class="purchase-item-license">' + p.license + '</span>' +
                    '</div>' +
                    '<div class="purchase-item-footer">' +
                        '<span>₹' + p.price_paid.toFixed(2) + ' &bull; ' + p.download_count + ' downloads</span>' +
                        '<a href="/download/' + p.product_id + '" class="purchase-download-btn"><i class="fas fa-download"></i> Download</a>' +
                    '</div>' +
                '</div>';
            }).join('');

        } catch (err) {
            list.innerHTML = '<div class="empty-purchases"><i class="fas fa-exclamation-circle"></i><p>Failed to load purchases</p></div>';
        }
    }

    // ==================== TOAST SYSTEM ====================
    var toastTimeout = null;
    var toastFadeTimeout = null;

    window.showToast = function(message, type) {
        type = type || 'info';
        if (toastTimeout) clearTimeout(toastTimeout);
        if (toastFadeTimeout) clearTimeout(toastFadeTimeout);

        var container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        var existingToasts = container.querySelectorAll('.toast');
        existingToasts.forEach(function(t) { t.remove(); });

        var toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.textContent = message;
        container.appendChild(toast);

        toast.offsetHeight;
        requestAnimationFrame(function() { toast.classList.add('show'); });

        toastTimeout = setTimeout(function() {
            toast.classList.add('toast-fading');
            toastFadeTimeout = setTimeout(function() { toast.remove(); }, 400);
        }, 3000);
    };

    // Toast CSS
    if (!document.querySelector('#toast-style')) {
        var style = document.createElement('style');
        style.id = 'toast-style';
        style.textContent = '.toast-container{position:fixed;bottom:30px;left:50%;transform:translateX(-50%);z-index:9999;pointer-events:none}.toast{background:var(--bg-elevated,#1e1e1e);color:var(--text-primary,#fff);padding:14px 24px;border-radius:40px;border:1px solid var(--border-mid,#333);font-weight:500;opacity:0;transform:translateY(100px);transition:all 0.3s ease;box-shadow:0 10px 30px rgba(0,0,0,0.3);pointer-events:auto}.toast.show{opacity:1;transform:translateY(0)}.toast.toast-fading{opacity:0;transform:translateY(20px)}.toast-success{border-color:#10b981;color:#10b981}.toast-error{border-color:#ef4444;color:#ef4444}.toast-info{border-color:#3b82f6;color:#3b82f6}';
        document.head.appendChild(style);
    }

    // ==================== MISC UI ====================
    mobileNavItems.forEach(function(item) {
        item.addEventListener('click', function() {
            mobileNavItems.forEach(function(n) { n.classList.remove('active'); });
            item.classList.add('active');
        });
    });

    if (header) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 40) header.classList.add('scrolled');
            else header.classList.remove('scrolled');
        });
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal(loginModal);
            closeModal(signupModal);
            closeUserSidebar();
            closeAccountModal();
        }
    });

    // ==================== AUTH STATUS CHECK ====================
    async function checkAuthStatus() {
        try {
            var res = await fetch('/api/auth/me');
            var data = await res.json();
            if (data.logged_in && data.user) {
                updateAuthUI(data.user);
            } else {
                updateAuthUI(null);
            }
        } catch (err) {
            updateAuthUI(null);
        }
    }

    window.setUserLoggedIn = function(userData) { updateAuthUI(userData); };
    window.setUserLoggedOut = function() { updateAuthUI(null); };

    document.addEventListener('DOMContentLoaded', function() {
        checkAuthStatus();
    });

})();
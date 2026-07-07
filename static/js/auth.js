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

    var guestAuthBtns = document.getElementById('guestAuthBtns');
    var userMenuBtns = document.getElementById('userMenuBtns');
    var headerUsername = document.getElementById('headerUsername');
    var header = document.querySelector('.site-header');

    var accountBtn = document.getElementById('accountBtn');
    var mobileAccountBtn = document.getElementById('mobileAccountBtn');
    var accountModal = document.getElementById('accountModal');
    var accountModalOverlay = document.getElementById('accountModalOverlay');
    var closeAccountModalBtn = document.getElementById('closeAccountModalBtn');

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

        if (currentUser) {
            loadAccountStats();
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

    // Login/Signup buttons
    if (openLoginBtn) openLoginBtn.addEventListener('click', function() { openModal(loginModal); });
    if (openSignupBtn) openSignupBtn.addEventListener('click', function() { openModal(signupModal); });
    if (closeLoginBtn) closeLoginBtn.addEventListener('click', function() { closeModal(loginModal); });
    if (closeSignupBtn) closeSignupBtn.addEventListener('click', function() { closeModal(signupModal); });

    // Account modal close
    if (closeAccountModalBtn) closeAccountModalBtn.addEventListener('click', closeAccountModal);
    if (accountModalOverlay) {
        accountModalOverlay.addEventListener('click', function(e) {
            if (e.target === accountModalOverlay) closeAccountModal();
        });
    }

    // Switch between login/signup
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

    // ==================== ACCOUNT BUTTON CLICK ====================
    function handleAccountClick() {
        openAccountModal();
    }

    if (accountBtn) accountBtn.addEventListener('click', handleAccountClick);
    if (mobileAccountBtn) mobileAccountBtn.addEventListener('click', function(e) {
        e.preventDefault();
        handleAccountClick();
    });

    // Account modal auth buttons (guest state)
    var accountLoginBtn = document.getElementById('accountLoginBtn');
    var accountSignupBtn = document.getElementById('accountSignupBtn');
    if (accountLoginBtn) accountLoginBtn.addEventListener('click', function() {
        closeAccountModal();
        setTimeout(function() { openModal(loginModal); }, 200);
    });
    if (accountSignupBtn) accountSignupBtn.addEventListener('click', function() {
        closeAccountModal();
        setTimeout(function() { openModal(signupModal); }, 200);
    });

    // Logout
    var logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);

    // ==================== LOAD QUICK STATS ====================
    async function loadAccountStats() {
        var purchaseCount = 0;

        try {
            var purchasesRes = await fetch('/api/user/purchases', { credentials: 'same-origin' });
            var purchasesData = await purchasesRes.json();
            var purchases = purchasesData.purchases || [];
            purchaseCount = purchases.length;
            var productCountEl = document.getElementById('accountProductCount');
            if (productCountEl) productCountEl.textContent = purchaseCount;
        } catch (e) {}

        try {
            var licensesRes = await fetch('/api/user/licenses', { credentials: 'same-origin' });
            var licensesData = await licensesRes.json();
            var licenses = licensesData.licenses || [];
            var licenseCountEl = document.getElementById('accountLicenseCount');
            if (licenseCountEl) licenseCountEl.textContent = licenses.length;
        } catch (e) {}

        try {
            var orderCountEl = document.getElementById('accountOrderCount');
            if (orderCountEl) orderCountEl.textContent = purchaseCount || 0;
        } catch (e) {}
    }

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
        var authPrompt = document.getElementById('accountAuthPrompt');
        var loggedIn = document.getElementById('accountLoggedIn');

        if (isLoggedIn && user) {
            if (modalUsername) modalUsername.textContent = user.username || 'User';
            if (modalEmail) modalEmail.textContent = user.email || 'Member';
            if (avatar) {
                avatar.innerHTML = '<span style="font-weight:800;font-size:1.2rem;">' +
                    (user.username ? user.username.charAt(0).toUpperCase() : 'U') + '</span>';
            }
            if (authPrompt) authPrompt.style.display = 'none';
            if (loggedIn) loggedIn.style.display = 'block';
        } else {
            if (modalUsername) modalUsername.textContent = 'Guest';
            if (modalEmail) modalEmail.textContent = 'Sign in to access your account';
            if (avatar) avatar.innerHTML = '<i class="fas fa-user-circle"></i>';
            if (authPrompt) authPrompt.style.display = 'block';
            if (loggedIn) loggedIn.style.display = 'none';
        }

        if (!isLoggedIn) {
            closeAccountModal();
        }
    }

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
                closeAccountModal();
            }
        } catch (err) {
            showToast('Logout failed', 'error');
        }
    }

    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    if (signupForm) signupForm.addEventListener('submit', handleSignup);

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
document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    // ==================== TAB SWITCHING ====================
    var tabs = document.querySelectorAll('.dash-tab');
    var contents = document.querySelectorAll('.dash-tab-content');

    if (tabs.length > 0) {
        tabs.forEach(function(tab) {
            tab.addEventListener('click', function() {
                var target = tab.dataset.tab;

                tabs.forEach(function(t) { t.classList.remove('active'); });
                contents.forEach(function(c) { c.classList.remove('active'); });

                tab.classList.add('active');
                var content = document.getElementById('tab-' + target);
                if (content) content.classList.add('active');
            });
        });
    }

    // ==================== EDIT PROFILE ====================
    var saveProfileBtn = document.getElementById('dashSaveProfileBtn');

    if (saveProfileBtn) {
        saveProfileBtn.addEventListener('click', async function() {
            var err = document.getElementById('dashProfileError');
            var suc = document.getElementById('dashProfileSuccess');
            var usernameInput = document.getElementById('dashEditUsername');
            var emailInput = document.getElementById('dashEditEmail');

            if (!usernameInput || !emailInput) return;

            var username = usernameInput.value.trim();
            var email = emailInput.value.trim();

            if (err) { err.style.display = 'none'; err.textContent = ''; }
            if (suc) { suc.style.display = 'none'; suc.textContent = ''; }

            if (!username && !email) {
                if (err) {
                    err.textContent = 'Please fill in at least one field';
                    err.style.display = 'block';
                }
                return;
            }

            saveProfileBtn.disabled = true;
            saveProfileBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

            try {
                var res = await fetch('/api/user/profile', {
                    method: 'PUT',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: username, email: email })
                });
                var data = await res.json();

                if (data.success) {
                    if (suc) {
                        suc.textContent = data.message || 'Profile updated!';
                        suc.style.display = 'block';
                    }
                    if (data.user) {
                        var settingsUsername = document.getElementById('dashSettingsUsername');
                        var settingsEmail = document.getElementById('dashSettingsEmail');
                        var dashUsername = document.getElementById('dashUsername');
                        if (settingsUsername) settingsUsername.textContent = data.user.username;
                        if (settingsEmail) settingsEmail.textContent = data.user.email;
                        if (dashUsername) dashUsername.textContent = data.user.username;
                    }
                    if (window.showToast) {
                        window.showToast('Profile updated successfully', 'success');
                    }
                } else {
                    if (err) {
                        err.textContent = data.error || data.message || 'Update failed';
                        err.style.display = 'block';
                    }
                }
            } catch (e) {
                console.error('Profile update error:', e);
                if (err) {
                    err.textContent = 'Network error. Please try again.';
                    err.style.display = 'block';
                }
            } finally {
                saveProfileBtn.disabled = false;
                saveProfileBtn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
            }
        });
    }

    // ==================== CHANGE PASSWORD ====================
    var changePwBtn = document.getElementById('dashChangePasswordBtn');

    if (changePwBtn) {
        changePwBtn.addEventListener('click', async function() {
            var err = document.getElementById('dashPasswordError');
            var suc = document.getElementById('dashPasswordSuccess');
            var curInput = document.getElementById('dashCurrentPassword');
            var nwInput = document.getElementById('dashNewPassword');
            var confInput = document.getElementById('dashConfirmPassword');

            if (!curInput || !nwInput || !confInput) return;

            var cur = curInput.value;
            var nw = nwInput.value;
            var conf = confInput.value;

            if (err) { err.style.display = 'none'; err.textContent = ''; }
            if (suc) { suc.style.display = 'none'; suc.textContent = ''; }

            if (!cur || !nw || !conf) {
                if (err) {
                    err.textContent = 'All fields are required';
                    err.style.display = 'block';
                }
                return;
            }

            if (nw.length < 6) {
                if (err) {
                    err.textContent = 'New password must be at least 6 characters';
                    err.style.display = 'block';
                }
                return;
            }

            if (nw !== conf) {
                if (err) {
                    err.textContent = 'New passwords do not match';
                    err.style.display = 'block';
                }
                return;
            }

            if (nw === cur) {
                if (err) {
                    err.textContent = 'New password must be different from current';
                    err.style.display = 'block';
                }
                return;
            }

            changePwBtn.disabled = true;
            changePwBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';

            try {
                var res = await fetch('/api/user/change-password', {
                    method: 'PUT',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        current_password: cur,
                        new_password: nw
                    })
                });
                var data = await res.json();

                if (data.success) {
                    if (suc) {
                        suc.textContent = data.message || 'Password changed!';
                        suc.style.display = 'block';
                    }
                    curInput.value = '';
                    nwInput.value = '';
                    confInput.value = '';
                    if (window.showToast) {
                        window.showToast('Password changed successfully', 'success');
                    }
                } else {
                    if (err) {
                        err.textContent = data.error || 'Failed to change password';
                        err.style.display = 'block';
                    }
                }
            } catch (e) {
                console.error('Password change error:', e);
                if (err) {
                    err.textContent = 'Network error. Please try again.';
                    err.style.display = 'block';
                }
            } finally {
                changePwBtn.disabled = false;
                changePwBtn.innerHTML = '<i class="fas fa-key"></i> Update Password';
            }
        });
    }

});
// admin.js — Admin panel interactions
'use strict';

document.addEventListener('DOMContentLoaded', function () {

window.toggleTypeFields = function (type) {
        var beat = document.getElementById('beatSection');
        var pack = document.getElementById('packFields');
        var preset = document.getElementById('presetFields');
        var nonBeat = document.getElementById('nonBeatFields');

        if (beat) beat.style.display = 'none';
        if (pack) pack.style.display = 'none';
        if (preset) preset.style.display = 'none';
        if (nonBeat) nonBeat.style.display = 'none';

        if (type === 'beat') {
            if (beat) beat.style.display = '';
        } else if (type === 'pack') {
            if (pack) pack.style.display = '';
            if (nonBeat) nonBeat.style.display = '';
        } else if (type === 'preset') {
            if (preset) preset.style.display = '';
            if (nonBeat) nonBeat.style.display = '';
        }
    };

    // ── Auto-dismiss flash messages ──
    var flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(function (flash) {
        setTimeout(function () {
            flash.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-10px)';
            setTimeout(function () {
                if (flash.parentNode) flash.remove();
            }, 300);
        }, 5000);
    });

    // ── Confirm delete actions ──
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (form.action && form.action.indexOf('/delete') !== -1) {
            if (!confirm('Are you sure you want to delete this item? This cannot be undone.')) {
                e.preventDefault();
            }
        }
    });

    // ── Confirm toggle admin ──
    document.querySelectorAll('form[action*="toggle-admin"]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!confirm('Change this user\'s admin status?')) {
                e.preventDefault();
            }
        });
    });

    // ── Price format ──
    document.querySelectorAll('input[name$="_price"], input[name="price"], input[name="min_order"], input[name="discount_value"]').forEach(function (input) {
        input.addEventListener('focus', function () {
            this.setAttribute('inputmode', 'decimal');
        });
    });

    // ── Product type change listener ──
    var typeSelect = document.getElementById('product_type');
    if (typeSelect) {
        // Run on load to set correct visibility
        toggleTypeFields(typeSelect.value);

        typeSelect.addEventListener('change', function () {
            toggleTypeFields(this.value);
        });
    }

    // ── Slug preview ──
    var nameInput = document.getElementById('name');
    if (nameInput) {
        var slugPreview = document.createElement('small');
        slugPreview.style.cssText = 'color:#666; font-size:0.75rem; display:block; margin-top:0.25rem;';
        nameInput.parentNode.appendChild(slugPreview);

        nameInput.addEventListener('input', function () {
            var slug = this.value.toLowerCase().trim()
                .replace(/[^\w\s-]/g, '')
                .replace(/[\s_]+/g, '-');
            slugPreview.textContent = slug ? 'Slug: /' + slug : '';
        });
    }

    console.log('Admin panel loaded');

    // ── Auto-dismiss flash messages ──
    var flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(function (flash) {
        setTimeout(function () {
            flash.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-10px)';
            setTimeout(function () {
                if (flash.parentNode) flash.remove();
            }, 300);
        }, 5000);
    });

    // ── Confirm delete actions (delegate) ──
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (form.action && form.action.indexOf('/delete') !== -1) {
            if (!confirm('Are you sure you want to delete this item? This cannot be undone.')) {
                e.preventDefault();
            }
        }
    });

    // ── Confirm toggle admin (self-demotion guard is server-side, but UX confirm helps) ──
    document.querySelectorAll('form[action*="toggle-admin"]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!confirm('Change this user\'s admin status?')) {
                e.preventDefault();
            }
        });
    });

    // ── Price format preview (show ₹ while typing) ──
    document.querySelectorAll('input[name$="_price"], input[name="price"], input[name="min_order"], input[name="discount_value"]').forEach(function (input) {
        input.addEventListener('focus', function () {
            this.setAttribute('inputmode', 'decimal');
        });
    });

    // ── Dynamic product type toggle (for add page) ──
    var typeSelect = document.getElementById('product_type');
    if (typeSelect) {
        typeSelect.addEventListener('change', function () {
            if (typeof toggleTypeFields === 'function') {
                toggleTypeFields(this.value);
            }
        });
    }

    // ── Slug preview (optional: show slug below name field) ──
    var nameInput = document.getElementById('name');
    if (nameInput) {
        var slugPreview = document.createElement('small');
        slugPreview.style.cssText = 'color:#666; font-size:0.75rem; display:block; margin-top:0.25rem;';
        nameInput.parentNode.appendChild(slugPreview);

        nameInput.addEventListener('input', function () {
            var slug = this.value.toLowerCase().trim()
                .replace(/[^\w\s-]/g, '')
                .replace(/[\s_]+/g, '-');
            slugPreview.textContent = slug ? 'Slug: /' + slug : '';
        });
    }

    console.log('Admin panel loaded');
});
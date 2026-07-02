// index.js — Homepage UI: preloader, tabs, scroll reveals, interactions
'use strict';

(function () {

    // ── Feature Detection ──────────────────────────────────────
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isTouchDevice = window.matchMedia('(pointer: coarse)').matches;



    // ── FLOATING NOTES ─────────────────────────────────────────
    var notesContainer = document.getElementById('floatingNotes');
    if (notesContainer && !prefersReducedMotion) {
        var noteSymbols = ['\u266A', '\u266B', '\u266C', '\u2669', '\u266D'];
        for (var i = 0; i < 24; i++) {
            var note = document.createElement('span');
            note.className = 'note';
            note.textContent = noteSymbols[Math.floor(Math.random() * noteSymbols.length)];
            note.style.left = (Math.random() * 100) + '%';
            note.style.animationDuration = (12 + Math.random() * 18) + 's';
            note.style.animationDelay = (Math.random() * 12) + 's';
            note.style.fontSize = (1.2 + Math.random() * 2.5) + 'rem';
            note.style.opacity = String(0.05 + Math.random() * 0.12);
            notesContainer.appendChild(note);
        }
    }

    // ── HEADER SCROLL EFFECT (throttled) ───────────────────────
    var header = document.getElementById('header');
    if (header) {
        var scrollTicking = false;
        window.addEventListener('scroll', function () {
            if (scrollTicking) return;
            scrollTicking = true;
            requestAnimationFrame(function () {
                if (window.scrollY > 40) {
                    header.classList.add('scrolled');
                } else {
                    header.classList.remove('scrolled');
                }
                scrollTicking = false;
            });
        });
    }

    // ── TABS ───────────────────────────────────────────────────
    var tabBtns = document.querySelectorAll('.tab-btn[data-tab]');
    var contents = document.querySelectorAll('.tab-content');

    function activateTab(tabId) {
        contents.forEach(function (c) { c.classList.remove('active'); });
        var activeContent = document.getElementById(tabId);
        if (activeContent) activeContent.classList.add('active');
        tabBtns.forEach(function (btn) {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });
    }

    tabBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            activateTab(btn.dataset.tab);
        });
    });

    // ── NAV SMOOTH SCROLLING ───────────────────────────────────
    document.querySelectorAll('nav a').forEach(function (link) {
        link.addEventListener('click', function (e) {
            var href = link.getAttribute('href');
            if (!href || !href.startsWith('#')) return;
            e.preventDefault();
            var targetId = href.substring(1);
            var element = document.getElementById(targetId);
            if (!element) return;
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            if (['beat-packs', 'vocal-presets', 'beats'].indexOf(targetId) !== -1) {
                activateTab(targetId);
            }
        });
    });

    // ── SCROLL REVEAL (Intersection Observer) ──────────────────
    var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                revealObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.reveal-on-scroll').forEach(function (el) {
        revealObserver.observe(el);
    });

    // ── MAGNETIC BUTTONS (desktop only, non-destructive) ───────
    if (!isTouchDevice) {
        document.querySelectorAll('.magnetic-btn').forEach(function (btn) {
            btn.addEventListener('mousemove', function (e) {
                var rect = btn.getBoundingClientRect();
                var x = (e.clientX - rect.left - rect.width / 2) * 0.15;
                var y = (e.clientY - rect.top - rect.height / 2) * 0.15;
                // Use a separate translate that won't conflict with hover transforms
                btn.style.setProperty('--mx', x + 'px');
                btn.style.setProperty('--my', y + 'px');
                btn.style.transform = 'translate(var(--mx), var(--my))';
            });
            btn.addEventListener('mouseleave', function () {
                btn.style.transform = '';
                btn.style.removeProperty('--mx');
                btn.style.removeProperty('--my');
            });
        });
    }

    // ── PARALLAX HERO VISUAL ───────────────────────────────────
    var heroVisual = document.querySelector('.hero-visual-wrapper');
    if (heroVisual && !prefersReducedMotion && !isTouchDevice) {
        var parallaxTicking = false;
        window.addEventListener('scroll', function () {
            if (parallaxTicking) return;
            parallaxTicking = true;
            requestAnimationFrame(function () {
                var rate = window.scrollY * 0.08;
                heroVisual.style.transform = 'translateY(' + rate + 'px)';
                parallaxTicking = false;
            });
        });
    }

    // ── WHATSAPP FLOAT — hide on fast scroll down ──────────────
    var whatsappFloat = document.getElementById('whatsappFloat');
    var lastScrollY = window.scrollY;
    if (whatsappFloat) {
        window.addEventListener('scroll', function () {
            var currentScrollY = window.scrollY;
            if (currentScrollY > lastScrollY && currentScrollY > 300) {
                whatsappFloat.classList.add('hidden');
            } else {
                whatsappFloat.classList.remove('hidden');
            }
            lastScrollY = currentScrollY;
        });
    }

    // ── MOBILE BOTTOM NAV ACTIVE STATE ─────────────────────────
    var mobileNavItems = document.querySelectorAll('.mobile-nav-item');
    mobileNavItems.forEach(function (item) {
        item.addEventListener('click', function () {
            mobileNavItems.forEach(function (n) { n.classList.remove('active'); });
            item.classList.add('active');
        });
    });

    // ── CLICK-DELEGATION FOR CART BUTTONS ON CARDS ─────────────
    // (replaces inline onclick with XSS risk from template injection)
    document.addEventListener('click', function (e) {
        var card = e.target.closest('.card[data-product-id]');
        if (!card) return;

        var product = {
            id: parseInt(card.dataset.productId, 10),
            name: card.dataset.productName,
            price: parseFloat(card.dataset.productPrice),
            type: card.dataset.productType
        };

        if (e.target.closest('.js-add-to-cart')) {
            if (typeof window.addToGlobalCart === 'function') {
                window.addToGlobalCart(product);
            }
        } else if (e.target.closest('.js-buy-now')) {
            if (typeof window.addToGlobalCart === 'function') {
                window.addToGlobalCart(product, true);
            }
        }
    });

    // ── LICENSE CARD CLICK DELEGATION (for license modal) ──────
    document.addEventListener('click', function (e) {
        var card = e.target.closest('.license-card[data-license]');
        if (card && typeof window.selectLicense === 'function') {
            window.selectLicense(card.dataset.license);
        }
    });

    console.log('XLOVEBEATS UI loaded');

})();
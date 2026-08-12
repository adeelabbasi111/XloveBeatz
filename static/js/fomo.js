// FOMO Notification System
document.addEventListener('DOMContentLoaded', function() {
    // Exclude admin pages
    if (window.location.pathname.includes('/admin')) return;

    let events = [];
    let currentIndex = 0;
    
    // Create container if it doesn't exist
    let container = document.getElementById('fomo-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'fomo-toast-container';
        document.body.appendChild(container);
    }

    // Fetch events from backend
    async function fetchFomoEvents() {
        try {
            const res = await fetch('/api/fomo-events');
            if (res.ok) {
                events = await res.json();
                if (events.length > 0) {
                    // Start the loop after a short initial delay
                    setTimeout(showNextEvent, 2000);
                }
            }
        } catch (e) {
            console.error('Failed to fetch FOMO events:', e);
        }
    }

    function isModalOpen() {
        const modals = document.querySelectorAll('.modal, .auth-modal');
        for (let i = 0; i < modals.length; i++) {
            const style = window.getComputedStyle(modals[i]);
            if (style.display !== 'none') return true;
        }
        const cart = document.getElementById('cartSidebar');
        if (cart && cart.classList.contains('open')) return true;
        return false;
    }

    function showNextEvent() {
        if (events.length === 0) return;

        // Schedule the next one at a random interval (between 20s and 30s) for ~2-3 per minute
        const nextInterval = Math.floor(Math.random() * (30000 - 20000 + 1)) + 20000;

        // Skip showing the toast if a modal is open, but keep the loop running
        if (isModalOpen()) {
            setTimeout(showNextEvent, nextInterval);
            return;
        }

        // Get current event and advance index
        const event = events[currentIndex];
        currentIndex = (currentIndex + 1) % events.length;

        // Create the toast element
        const toast = document.createElement('div');
        toast.className = `fomo-toast fomo-type-${event.type}`;
        
        toast.innerHTML = `
            <div class="fomo-icon-wrapper">
                <i class="${event.icon}"></i>
            </div>
            <div class="fomo-content">
                <div class="fomo-message">${event.message}</div>
                ${event.time ? `<div class="fomo-time">${event.time}</div>` : ''}
            </div>
        `;

        // Add to container
        container.appendChild(toast);

        // Animate in (allow DOM to update first)
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                toast.classList.add('show');
            });
        });

        // Remove after 6 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            toast.classList.add('hide');
            
            // Wait for transition, then remove from DOM
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 500);
        }, 6000);

        setTimeout(showNextEvent, nextInterval);
    }

    // Init
    fetchFomoEvents();
});

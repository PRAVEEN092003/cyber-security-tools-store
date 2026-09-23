/**
 * script.js — CYBERSEC STORE
 * ----------------------------------------
 * Clean, lightweight, professional UI interactions:
 * - Navbar scroll styling
 * - Accessible password toggle
 * - Auto-dismissing flash messages
 * - Numeric stat counters
 */

'use strict';

// ---------------------------------------------------------------------------
// 1. NAVBAR SCROLL EFFECT
// ---------------------------------------------------------------------------
(function initNavbarScroll() {
    const navbar = document.getElementById('mainNavbar');
    if (!navbar) return;

    const onScroll = () => {
        if (window.scrollY > 20) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
})();


// ---------------------------------------------------------------------------
// 2. FLASH MESSAGE AUTO-DISMISS & ANIMATION
// ---------------------------------------------------------------------------
(function initFlashDismissal() {
    document.addEventListener('DOMContentLoaded', () => {
        const alerts = document.querySelectorAll('.cs-flash-alert');
        alerts.forEach(alert => {
            setTimeout(() => {
                alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-8px)';
                setTimeout(() => alert.remove(), 400);
            }, 5000);
        });
    });
})();


// ---------------------------------------------------------------------------
// 3. PASSWORD VISIBILITY TOGGLE (ACCESSIBLE & SEAMLESS)
// ---------------------------------------------------------------------------
(function initPasswordToggles() {
    document.addEventListener('DOMContentLoaded', () => {
        // Wire up existing in-template toggle buttons
        document.querySelectorAll('.toggle-password-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const group = btn.closest('.input-group') || btn.parentElement;
                const input = group ? group.querySelector('input[type="password"], input[type="text"]') : null;
                if (!input) return;
                const isPassword = input.type === 'password';
                input.type = isPassword ? 'text' : 'password';
                const icon = btn.querySelector('i');
                if (icon) {
                    icon.className = isPassword ? 'bi bi-eye-slash text-cs-accent' : 'bi bi-eye';
                }
                btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
            });
        });

        // Fallback for any password inputs that don't have markup buttons
        const unboundInputs = document.querySelectorAll('input[type="password"]');
        unboundInputs.forEach(input => {
            const wrapper = input.parentElement;
            if (!wrapper || wrapper.querySelector('.toggle-password-btn')) return;

            wrapper.style.position = 'relative';

            const toggleBtn = document.createElement('button');
            toggleBtn.type = 'button';
            toggleBtn.className = 'btn btn-link toggle-password-btn';
            toggleBtn.setAttribute('aria-label', 'Toggle password visibility');
            toggleBtn.style.cssText = `
                position: absolute;
                right: 12px;
                top: 50%;
                transform: translateY(-50%);
                color: #64748b;
                padding: 0;
                font-size: 1.1rem;
                z-index: 5;
                text-decoration: none;
                border: none;
                background: transparent;
            `;
            toggleBtn.innerHTML = '<i class="bi bi-eye"></i>';

            toggleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const isPassword = input.type === 'password';
                input.type = isPassword ? 'text' : 'password';
                toggleBtn.innerHTML = isPassword ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';
                toggleBtn.style.color = isPassword ? '#00f0ff' : '#64748b';
            });

            wrapper.appendChild(toggleBtn);
        });
    });
})();


// ---------------------------------------------------------------------------
// 4. STAT COUNTERS (SMOOTH & LIGHTWEIGHT)
// ---------------------------------------------------------------------------
(function initCounters() {
    document.addEventListener('DOMContentLoaded', () => {
        const counters = document.querySelectorAll('.counter-value');
        if (!counters.length) return;

        const animateCounter = (el) => {
            const rawTarget = el.getAttribute('data-target') || el.innerText;
            const target = parseFloat(rawTarget.replace(/[^0-9.-]+/g, ''));
            if (isNaN(target)) return;

            const isCurrency = rawTarget.includes('₹') || rawTarget.includes('$');
            const duration = 900;
            const startTime = performance.now();

            const update = (now) => {
                const elapsed = now - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const ease = 1 - (1 - progress) * (1 - progress);
                const current = target * ease;

                if (isCurrency) {
                    el.innerText = '₹' + current.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                } else if (Number.isInteger(target)) {
                    el.innerText = Math.round(current).toLocaleString();
                } else {
                    el.innerText = current.toFixed(1);
                }

                if (progress < 1) {
                    requestAnimationFrame(update);
                } else {
                    el.innerText = isCurrency ? '₹' + target.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : target.toLocaleString();
                }
            };

            requestAnimationFrame(update);
        };

        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.2 });

        counters.forEach(c => observer.observe(c));
    });
})();

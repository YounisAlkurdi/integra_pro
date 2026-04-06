/**
 * Integra SaaS Platform Scripts
 * Handles custom cursors, animations, pricing toggles, and modal logic.
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize Icons
    lucide.createIcons();

    // 2. Custom Cursor Logic
    const cursor = document.getElementById('cursor');
    const hoverTargets = document.querySelectorAll('.hover-target, button, a, input');

    if (cursor) {
        document.addEventListener('mousemove', (e) => {
            cursor.style.left = e.clientX + 'px';
            cursor.style.top = e.clientY + 'px';
        });

        hoverTargets.forEach(target => {
            target.addEventListener('mouseenter', () => {
                cursor.classList.add('hovering');
            });
            target.addEventListener('mouseleave', () => {
                cursor.classList.remove('hovering');
            });
        });
    }

    // 3. Reveal Animations
    const revealElements = document.querySelectorAll('.reveal');
    const exposeObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                observer.unobserve(entry.target); 
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: "0px"
    });

    revealElements.forEach(el => exposeObserver.observe(el));

    // 4. Init Fake Dashboard 
    initDashboard();
});

// --- Modal Controls ---
function toggleModal(modalId) {
    const overlay = document.getElementById(modalId);
    if (!overlay) return;

    const content = overlay.querySelector('.glass-panel');

    if (overlay.classList.contains('open')) {
        // Close animation
        if(content) {
            content.style.transform = 'scale(0.95)';
            content.style.opacity = '0';
        }
        overlay.classList.remove('open');
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 400);
    } else {
        // Open animation
        overlay.style.display = 'flex';
        setTimeout(() => {
            overlay.classList.add('open');
            if(content) {
                content.style.transform = 'scale(1)';
                content.style.opacity = '1';
                content.style.transition = 'all 0.5s cubic-bezier(0.19, 1, 0.22, 1)';
            }
        }, 10);
    }
}

// Close modals when clicking outside
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            toggleModal(overlay.id);
        }
    });
});

// Auth Form Simulations
function authSuccess() {
    toggleModal('auth-modal');
    setTimeout(() => {
        alert("Authentication Vector Confirmed. Welcome back.");
    }, 400);
}

function simulateLogout() {
    toggleModal('auth-modal');
    setTimeout(() => {
        alert("Connection Severed. Forced Logout Executed.");
    }, 400);
}

// --- Pricing Toggle Logic ---
let isYearly = false;

function toggleBilling() {
    isYearly = !isYearly;
    const knob = document.getElementById('toggle-knob');
    const labelMonthly = document.getElementById('label-monthly');
    const labelYearly = document.getElementById('label-yearly');
    const priceAmounts = document.querySelectorAll('.price-val');
    const billingBtn = document.getElementById('billing-toggle');

    if (isYearly) {
        knob.style.transform = 'translateX(24px)';
        billingBtn.classList.replace('bg-slate-800', 'bg-cyan-500');
        billingBtn.classList.replace('border-slate-700', 'border-cyan-400');
        labelMonthly.style.color = '#64748b'; // slate-500
        labelYearly.style.color = '#fff';

        priceAmounts.forEach(price => {
            animateValue(price, parseInt(price.dataset.monthly), parseInt(price.dataset.yearly), 300);
        });
    } else {
        knob.style.transform = 'translateX(0)';
        billingBtn.classList.replace('bg-cyan-500', 'bg-slate-800');
        billingBtn.classList.replace('border-cyan-400', 'border-slate-700');
        labelMonthly.style.color = '#fff';
        labelYearly.style.color = '#64748b';

        priceAmounts.forEach(price => {
            animateValue(price, parseInt(price.dataset.yearly), parseInt(price.dataset.monthly), 300);
        });
    }
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// --- Dashboard Simulation Logic ---
function initDashboard() {
    const barsContainer = document.getElementById('chart-bars');
    const liveLogs = document.getElementById('live-logs');
    
    if (!barsContainer || !liveLogs) return;

    for(let i=0; i<12; i++) {
        const bar = document.createElement('div');
        bar.className = 'flex-1 bg-cyan-500/20 border border-cyan-500/30 rounded-t-sm transition-all duration-1000 ease-in-out';
        bar.style.height = `${Math.floor(Math.random() * 60 + 20)}%`;
        barsContainer.appendChild(bar);
    }

    setInterval(() => {
        Array.from(barsContainer.children).forEach(bar => {
            bar.style.height = `${Math.floor(Math.random() * 80 + 10)}%`;
            // Randomly highlight bars
            if(Math.random() > 0.8) {
                bar.classList.add('bg-cyan-400');
                bar.classList.remove('bg-cyan-500/20');
                setTimeout(() => {
                    bar.classList.remove('bg-cyan-400');
                    bar.classList.add('bg-cyan-500/20');
                }, 1000);
            }
        });
    }, 2000);

    const logMessages = [
        "<span class='text-slate-500'>[SYSTEM]</span> Scanning inbound neural frequency...",
        "<span class='text-green-400'>[VERIFIED]</span> Handshake protocol matched.",
        "<span class='text-slate-500'>[TRACE]</span> Analyzing visual artifacts array #9928...",
        "<span class='text-green-400'>[SECURE]</span> No deepfake anomalies detected.",
        "<span class='text-cyan-400'>[HEURISTIC]</span> Biometric keystroke match: 98.4%",
        "<span class='text-red-400 font-bold'>[WARN]</span> Synthetic voice fluctuation detected! Filtering...",
        "<span class='text-slate-500'>[SYS]</span> Recalibrating cluster nodes."
    ];

    function appendLog() {
        const p = document.createElement('p');
        p.className = 'animate-pulse text-xs';
        setTimeout(() => p.classList.remove('animate-pulse'), 1000);
        p.innerHTML = logMessages[Math.floor(Math.random() * logMessages.length)];
        
        liveLogs.prepend(p);
        
        if(liveLogs.children.length > 8) {
            liveLogs.lastChild.remove();
        }
    }

    setInterval(appendLog, 1500);
    appendLog();
}

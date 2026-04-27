/**
 * Integra SaaS Platform Scripts
 * Handles custom cursors, animations, pricing toggles, and modal logic.
 */

// Global Logout Utility
window.logoutHR = async () => {
    if (window.supabase) {
        await window.supabase.auth.signOut();
        window.location.href = 'index.html';
    } else {
        window.location.href = 'index.html';
    }
};

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

    // 5. Initialize FramePlayer (Canvas Scroll Engine)
    if (document.getElementById('integra-canvas')) {
        new FramePlayer({ id: 'integra-canvas', totalFrames: 61 });
    }

    // 6. Load Pricing Data from JSON
    loadPricing();

    // 7. Enable 3D Motion Protocols
    init3DHover();
});

/**
 * FramePlayer Class - Optimized for Zero-Latency Scrubbing
 */
class FramePlayer {
    constructor(config) {
        this.canvas = document.getElementById(config.id);
        this.ctx = this.canvas.getContext('2d');
        this.totalFrames = config.totalFrames;
        this.frames = [];
        this.currentFrame = -1;
        this.isLoaded = false;
        this.isActive = false;
        this.config = config;
        
        this.state = {
            targetProgress: 0,
            currentProgress: 0,
            lerpFactor: 0.2, // Increased speed (from 0.1 to 0.2)
            isAnimating: false
        };

        this.init();
    }

    init() {
        this.container = document.querySelector('.scroll-container');
        if (!this.container) return;

        // Preload
        let loadedCount = 0;
        for (let i = 1; i <= this.totalFrames; i++) {
            const img = new Image();
            img.src = `../../assets/frames/ezgif-frame-${i.toString().padStart(3, '0')}.jpg`;
            img.onload = () => {
                loadedCount++;
                
                // Optimized: Show first frame as soon as it's ready
                if (i === 1) {
                    this.isLoaded = true;
                    this.onResize();
                    this.render();
                }

                if (loadedCount === this.totalFrames) {
                    this.syncTarget();
                }
            };
            this.frames.push(img);
        }

        // Intersection Observer for performance
        const observer = new IntersectionObserver((entries) => {
            this.isActive = entries[0].isIntersecting;
            if (this.isActive) this.syncTarget();
        }, { threshold: 0 });
        observer.observe(this.container);

        window.addEventListener('scroll', () => {
            if (this.isActive && this.isLoaded) this.syncTarget();
        }, { passive: true });
        
        window.addEventListener('resize', () => this.onResize());
    }

    onResize() {
        if (this.frames[0]) {
            this.canvas.width = this.frames[0].naturalWidth;
            this.canvas.height = this.frames[0].naturalHeight;
        }
        if (this.isActive) this.syncTarget();
    }

    syncTarget() {
        const rect = this.container.getBoundingClientRect();
        const progress = Math.abs(rect.top) / (rect.height - window.innerHeight);
        this.state.targetProgress = Math.max(0, Math.min(1, progress));
        
        if (!this.state.isAnimating) {
            this.state.isAnimating = true;
            requestAnimationFrame(() => this.render());
        }
    }

    render() {
        if (!this.isLoaded) return;

        const delta = this.state.targetProgress - this.state.currentProgress;
        this.state.currentProgress += delta * this.state.lerpFactor;

        const frameIndex = Math.floor(this.state.currentProgress * (this.totalFrames - 1));
        
        if (frameIndex !== this.currentFrame) {
            this.currentFrame = frameIndex;
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.drawImage(this.frames[frameIndex], 0, 0);
        }

        if (Math.abs(delta) > 0.0001 && this.isActive) {
            requestAnimationFrame(() => this.render());
        } else {
            this.state.isAnimating = false;
        }
    }
}

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

// --- Pricing Data Fetch & Render ---
async function loadPricing() {
    const grid = document.getElementById('pricing-grid');
    if (!grid) return;

    try {
        const response = await fetch('../../data/pricing.json');
        const data = await response.json();
        const plans = data.pricing_data.plans;

        grid.innerHTML = ''; // Clear skeleton

        plans.forEach((plan, index) => {
            const card = document.createElement('div');
            const delay = index * 0.1;
            
            // Special classes for highlighted plan
            const highlightClasses = plan.highlight ? 'relative lg:z-10' : '';
            const borderClasses = plan.highlight ? 'border-t-4 border-cyan-400' : '';
            const titleClasses = plan.highlight ? 'text-cyan-400' : 'text-white';
            const buttonClasses = plan.highlight 
                ? 'bg-cyan-400 text-obsidian border-cyan-400 hover:bg-white' 
                : 'border-white/20 hover:bg-white hover:text-black';

            card.className = `bg-obsidian p-12 reveal hover-target ${highlightClasses}`;
            card.style.transitionDelay = `${delay}s`;
            
            card.innerHTML = `
                ${plan.highlight ? `<div class="absolute top-0 left-0 w-full h-1 bg-cyan-400"></div>` : ''}
                ${plan.badge ? `<div class="absolute top-8 right-8 text-[9px] uppercase tracking-widest font-bold text-obsidian bg-cyan-400 px-3 py-1 rounded-full">${plan.badge}</div>` : ''}
                
                <h3 class="text-2xl font-bold mb-4 uppercase tracking-tighter ${titleClasses}">${plan.name}</h3>
                <p class="text-white/40 text-sm font-light mb-12 pb-8 border-b border-white/5 lowercase first-letter:uppercase">${plan.tagline}</p>
                
                <div class="mb-12 h-20 flex items-baseline">
                    ${plan.monthly.price === 'Custom' ? `
                        <span class="text-4xl font-bold tracking-tighter text-white">Custom</span>
                    ` : `
                        <span class="text-3xl font-light text-white/50">$</span>
                        <span class="text-6xl font-bold tracking-tighter price-val ${plan.highlight ? 'text-white' : ''}" 
                              data-monthly="${plan.monthly.price}" 
                              data-yearly="${plan.yearly.price}">
                              ${isYearly ? plan.yearly.price : plan.monthly.price}
                        </span>
                        <span class="text-white/40 font-mono text-xs uppercase tracking-widest ml-2">/mo</span>
                    `}
                </div>

                <ul class="space-y-6 mb-12 text-sm text-white/70 font-light">
                    ${plan.features.map(f => `
                        <li class="flex items-center gap-4"><div class="w-1 h-1 bg-cyan-400 rounded-full"></div> ${f}</li>
                    `).join('')}
                </ul>

                <button class="w-full py-4 border text-xs uppercase tracking-widest font-bold transition-all rounded-full ${buttonClasses}" 
                        onclick="window.location.href='checkout.html?plan=${plan.id}'">
                    ${plan.button_text}
                </button>
            `;

            grid.appendChild(card);
        });

        // Initialize animations and hover effects for new elements
        lucide.createIcons();
        const newRevealElements = grid.querySelectorAll('.reveal');
        newRevealElements.forEach(el => el.classList.add('active')); // Immediate activation for loaded cards
        
        init3DHover(); // Re-init hover for new cards
        initCursorForNewElements(); // Update cursor

    } catch (error) {
        console.error("Critical Security Breach: Failed to load pricing protocols.", error);
        grid.innerHTML = `<div class="col-span-3 py-20 text-center text-red-500 font-mono">[ ERROR: PRICING_PROTOCOL_OFFLINE ]</div>`;
    }
}

function initCursorForNewElements() {
    const cursor = document.getElementById('cursor');
    if (!cursor) return;
    const hoverTargets = document.querySelectorAll('.hover-target, button, a, input');
    
    hoverTargets.forEach(target => {
        target.removeEventListener('mouseenter', () => cursor.classList.add('hovering'));
        target.removeEventListener('mouseleave', () => cursor.classList.remove('hovering'));
        target.addEventListener('mouseenter', () => cursor.classList.add('hovering'));
        target.addEventListener('mouseleave', () => cursor.classList.remove('hovering'));
    });
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
        labelMonthly.style.color = '#64748b'; 
        labelYearly.style.color = '#fff';

        priceAmounts.forEach(price => {
            const start = parseInt(price.dataset.monthly);
            const end = parseInt(price.dataset.yearly);
            animateValue(price, start, end, 400);
        });
    } else {
        knob.style.transform = 'translateX(0)';
        billingBtn.classList.replace('bg-cyan-500', 'bg-slate-800');
        billingBtn.classList.replace('border-cyan-400', 'border-slate-700');
        labelMonthly.style.color = '#fff';
        labelYearly.style.color = '#64748b';

        priceAmounts.forEach(price => {
            const start = parseInt(price.dataset.yearly);
            const end = parseInt(price.dataset.monthly);
            animateValue(price, start, end, 400);
        });
    }
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        // Easing function for smoother feel
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        obj.innerHTML = Math.floor(easeProgress * (end - start) + start);
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

/**
 * 3D Hover Effect for Pricing Cards
 */
function init3DHover() {
    const cards = document.querySelectorAll('#pricing .reveal');
    
    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            // Limit tilt intensity
            const rotateX = (y - centerY) / 10; 
            const rotateY = (centerX - x) / 10;
            
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.05, 1.05, 1.05)`;
            card.style.zIndex = "10";
            card.style.boxShadow = "0 25px 50px -12px rgba(0, 255, 255, 0.2)";
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
            card.style.zIndex = "1";
            card.style.boxShadow = "none";
        });
        
        // Ensure smooth return
        card.style.transition = 'transform 0.15s ease-out, box-shadow 0.3s ease';
    });
}

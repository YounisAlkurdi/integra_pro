/**
 * Integra Pricing Page Logic
 * Handles interactive billing toggles, animations, and tiers.
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize Icons
    if (window.lucide) {
        lucide.createIcons();
    }

    // 2. Custom Cursor Sync
    const cursor = document.getElementById('cursor');
    if (cursor) {
        document.addEventListener('mousemove', (e) => {
            cursor.style.left = e.clientX + 'px';
            cursor.style.top = e.clientY + 'px';
        });

        // Delegate hover effects to parent to handle dynamic content
        document.body.addEventListener('mouseover', (e) => {
            if (e.target.classList.contains('hover-target') || 
                e.target.closest('.hover-target') ||
                ['BUTTON', 'A', 'INPUT'].includes(e.target.tagName)) {
                cursor.classList.add('hovering');
            }
        });

        document.body.addEventListener('mouseout', (e) => {
            if (e.target.classList.contains('hover-target') || 
                e.target.closest('.hover-target') ||
                ['BUTTON', 'A', 'INPUT'].includes(e.target.tagName)) {
                cursor.classList.remove('hovering');
            }
        });
    }

    // 3. Billing Toggle State
    let isYearly = false;
    const billingBtn = document.getElementById('billing-toggle');
    
    if (billingBtn) {
        window.toggleBilling = () => {
            isYearly = !isYearly;
            updateBillingUI(isYearly);
        };
    }

    window.selectPlan = (planId) => {
        if (planId === 'enterprise') {
            window.location.href = 'mailto:sales@integra.com';
            return;
        }
        
        const mode = isYearly ? 'yearly' : 'monthly';
        // Redirect to checkout with protocol parameters
        window.location.href = `checkout.html?plan=${planId}&mode=${mode}`;
    };

    function updateBillingUI(yearly) {
        const knob = document.getElementById('toggle-knob');
        const toggle = document.getElementById('billing-toggle');
        const labelMonthly = document.getElementById('label-monthly');
        const labelYearly = document.getElementById('label-yearly');
        const prices = document.querySelectorAll('.price-val');

        if (yearly) {
            knob.style.transform = 'translateX(32px)';
            toggle.classList.replace('bg-slate-800', 'bg-cyan-500');
            labelMonthly.classList.replace('text-white', 'text-slate-500');
            labelYearly.classList.replace('text-slate-500', 'text-white');
            
            prices.forEach(p => {
                const monthly = parseInt(p.dataset.monthly);
                const yearlyVal = parseInt(p.dataset.yearly);
                animateValue(p, monthly, yearlyVal, 600);
            });
        } else {
            knob.style.transform = 'translateX(0)';
            toggle.classList.replace('bg-cyan-500', 'bg-slate-800');
            labelMonthly.classList.replace('text-slate-500', 'text-white');
            labelYearly.classList.replace('text-white', 'text-slate-500');

            prices.forEach(p => {
                const monthly = parseInt(p.dataset.monthly);
                const yearlyVal = parseInt(p.dataset.yearly);
                animateValue(p, yearlyVal, monthly, 600);
            });
        }
    }

    // 4. Value Re-Animator (Numeric Morph)
    function animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            // Cubic-out easing for "premium" feel
            const ease = 1 - Math.pow(1 - progress, 3);
            obj.innerHTML = Math.floor(ease * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }

    // 5. Card 3D Tilt Logic
    const init3DHover = () => {
        const cards = document.querySelectorAll('#pricing-grid > div');
        cards.forEach(card => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                
                const rotateX = (y - centerY) / 20; 
                const rotateY = (centerX - x) / 20;
                
                card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
                card.style.zIndex = "10";
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
                card.style.zIndex = "1";
            });
            
            card.style.transition = 'transform 0.1s ease-out';
        });
    };

    init3DHover();
});

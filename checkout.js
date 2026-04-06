/**
 * checkout.js - Interactive Credit Card Logic
 * Handles real-time updates and 3D flip animations
 */

document.addEventListener('DOMContentLoaded', () => {
    // Input Elements
    const inputNumber = document.getElementById('input-number');
    const inputHolder = document.getElementById('input-holder');
    const inputExpiry = document.getElementById('input-expiry');
    const inputCvc = document.getElementById('input-cvc');

    // Display Elements
    const displayNumber = document.getElementById('card-number-display');
    const displayHolder = document.getElementById('card-holder-display');
    const displayExpiry = document.getElementById('card-expiry-display');
    const displayCvc = document.getElementById('card-cvc-display');

    const cardInner = document.getElementById('card-inner');

    // --- 3D Tilt & Glow Logic (State Driven) ---
    const cardContainer = document.querySelector('.card-container');
    const cardGlow = document.querySelector('.card-glow');
    
    let isFlipped = false;
    let isHovering = false;
    let isFlipping = false;
    let rotation = { x: 0, y: 0 };

    function updateTransform() {
        const baseY = isFlipped ? 180 : 0;
        
        // Disable tilt while in the middle of a 180-degree flip
        const targetX = (isHovering && !isFlipping) ? rotation.x : 0;
        const targetY = (isHovering && !isFlipping) ? (baseY + rotation.y) : baseY;
        
        // Final stable transform - rotate only
        cardInner.style.transform = `rotateY(${targetY}deg) rotateX(${targetX}deg)`;
    }

    cardContainer.addEventListener('mousemove', (e) => {
        isHovering = true;
        const rect = cardContainer.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        // Subtle tilt (1/25 ratio)
        rotation.x = (centerY - y) / 25;
        rotation.y = (x - centerX) / 25;

        if (!isFlipping) {
            // Very short transition for reactive feel
            cardInner.style.transition = 'transform 0.1s linear';
            updateTransform();
        }
        
        // Glow effect
        if (cardGlow) {
            cardGlow.style.opacity = '1';
            cardGlow.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(34, 211, 238, 0.15), transparent 60%)`;
        }
    });

    cardContainer.addEventListener('mouseleave', () => {
        isHovering = false;
        if (!isFlipping) {
            // Smooth return to base
            cardInner.style.transition = 'transform 0.5s ease';
            rotation.x = 0;
            rotation.y = 0;
            updateTransform();
        }
        if (cardGlow) cardGlow.style.opacity = '0';
    });

    // --- Flip Function ---
    const flip = (back) => {
        if (isFlipped === back) return;
        
        isFlipped = back;
        isFlipping = true;
        
        // Clean, stable transition for the flip
        cardInner.style.transition = 'transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
        updateTransform();
        
        if (back) cardInner.classList.add('flipped');
        else cardInner.classList.remove('flipped');

        // Lock out tilt interactions during animation
        setTimeout(() => {
            isFlipping = false;
        }, 600);
    };

    // --- Form Inputs Listeners ---
    inputCvc.addEventListener('focus', () => flip(true));
    inputExpiry.addEventListener('focus', () => flip(true));
    inputNumber.addEventListener('focus', () => flip(false));
    inputHolder.addEventListener('focus', () => flip(false));

    // Card Number Formatting
    inputNumber.addEventListener('input', (e) => {
        let value = e.target.value.replace(/\D/g, ''); 
        let formattedValue = '';
        for (let i = 0; i < value.length; i++) {
            if (i > 0 && i % 4 === 0) formattedValue += ' ';
            formattedValue += value[i];
        }
        e.target.value = formattedValue.substring(0, 19);
        displayNumber.textContent = e.target.value || '0000 0000 0000 0000';
    });

    // Holder Name
    inputHolder.addEventListener('input', (e) => {
        displayHolder.textContent = e.target.value.toUpperCase() || 'JANE DOE';
    });

    // Expiry
    inputExpiry.addEventListener('input', (e) => {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length > 2) {
            value = value.substring(0, 2) + '/' + value.substring(2, 4);
        }
        e.target.value = value;
        displayExpiry.textContent = value || 'MM/YY';
    });

    // CVC
    inputCvc.addEventListener('input', (e) => {
        displayCvc.textContent = e.target.value.replace(/./g, '•') || '•••';
    });
});

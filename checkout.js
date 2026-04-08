let stripe, elements, card;
let currentPlan = null;
let billingMode = 'monthly'; // default
let planId = new URLSearchParams(window.location.search).get('plan') || 'starter';

// Dynamic Initialization Node
async function initializeStripe() {
    const endpoints = window.INTEGRA_SETTINGS.API_FALLBACK_URLS.map(url => `${url}/config`);

    let publishableKey = null;

    for (let url of endpoints) {
        try {
            console.log(`=> Neural Link: Attempting connection via ${url}`);
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                publishableKey = data.publishableKey;
                console.log(`=> Neural Link: Success via ${url}`);
                break;
            }
        } catch (e) {
            continue;
        }
    }

    if (publishableKey) {
        stripe = Stripe(publishableKey);
    } else {
        console.warn("=> Neural Link: Backend Unreachable. Using Fallback.");
        stripe = Stripe('pk_test_placeholder');
    }

    elements = stripe.elements();
    card = elements.create('card', {
        style: {
            base: {
                color: '#ffffff',
                fontFamily: '"Space Mono", monospace',
                fontSize: '14px',
                '::placeholder': { color: 'rgba(255, 255, 255, 0.1)' },
                iconColor: '#22d3ee'
            },
            invalid: { color: '#ef4444' }
        }
    });

    card.mount('#card-element');
    
    // Load Plan Details
    loadPlanData();
}

async function loadPlanData() {
    try {
        const response = await fetch('pricing.json');
        const data = await response.json();
        currentPlan = data.pricing_data.plans.find(p => p.id === planId);

        if (currentPlan) {
            updatePriceDisplays();
        }
    } catch (e) {
        console.error("=> Identity Breach: Failed to load pricing protocols.", e);
    }
}

function updatePriceDisplays() {
    if (!currentPlan) return;

    const monthlyDisplay = document.getElementById('monthly-price-display');
    const yearlyDisplay = document.getElementById('yearly-price-display');

    if (currentPlan.monthly.price === 'Custom') {
        monthlyDisplay.textContent = 'Custom Tier';
        yearlyDisplay.textContent = 'Custom Tier';
    } else {
        monthlyDisplay.textContent = `$${currentPlan.monthly.price}.00/month + tax`;
        const totalYearly = currentPlan.yearly.price * 12;
        yearlyDisplay.textContent = `$${totalYearly}.00/year + tax`;
    }
}

function selectBilling(mode) {
    billingMode = mode;
    
    // UI Update
    document.getElementById('billing-monthly').classList.toggle('active-billing', mode === 'monthly');
    document.getElementById('billing-yearly').classList.toggle('active-billing', mode === 'yearly');
}

initializeStripe();

// 3D Experience (Physics Engine)
const cardInner = document.getElementById('card-inner');
const cardContainer = document.querySelector('.card-container');

cardContainer.addEventListener('mousemove', (e) => {
    const rect = cardContainer.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    cardInner.style.transition = 'transform 0.1s linear';
    cardInner.style.transform = `rotateX(${-y * 25}deg) rotateY(${x * 25}deg)`;
});

cardContainer.addEventListener('mouseleave', () => {
    cardInner.style.transition = 'transform 0.6s ease';
    cardInner.style.transform = 'rotateY(0deg) rotateX(0deg)';
});

// Identity Sync
const holderInput = document.getElementById('card-holder-name');
const holderDisplay = document.getElementById('card-holder-display');

holderInput.addEventListener('input', (e) => {
    holderDisplay.textContent = e.target.value.toUpperCase() || 'JANE DOE';
});

// Force Handle
const form = document.getElementById('payment-form');
const button = document.getElementById('submit-button');

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    button.disabled = true;
    button.textContent = 'AUTHENTICATING...';

    const { paymentMethod, error } = await stripe.createPaymentMethod({
        type: 'card',
        card: card,
        billing_details: { name: holderInput.value }
    });

    if (error) {
        document.getElementById('card-errors').textContent = error.message;
        button.disabled = false;
        button.textContent = 'Confirm Secure Transaction';
    } else {
        await processPayment(paymentMethod.id);
    }
});

async function processPayment(paymentMethodId) {
    if (!currentPlan) return;

    let amount = 0;
    if (currentPlan.monthly.price === 'Custom') {
        alert("Consultation required for Enterprise Tier.");
        button.disabled = false;
        button.textContent = 'Contact Sales';
        return;
    }

    // Stripe amount is in cents
    if (billingMode === 'monthly') {
        amount = currentPlan.monthly.price * 100;
    } else {
        amount = currentPlan.yearly.price * 12 * 100;
    }

    try {
        const response = await fetch(window.INTEGRA_SETTINGS.endpoint('/create-payment-intent'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                payment_method_id: paymentMethodId, 
                amount: amount,
                plan_id: planId,
                billing_cycle: billingMode
            })
        });
        const result = await response.json();
        if (result.status === 'success') {
            window.location.href = 'index.html?status=success&plan=' + planId;
        } else {
            alert('Security Link Severed: ' + result.message);
        }
    } catch (err) {
        console.error("=> System Critical Error: ", err);
        button.disabled = false;
        button.textContent = 'Retry Handshake';
    }
}

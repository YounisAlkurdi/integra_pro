let stripe, elements, cardNumber, cardExpiry, cardCvc;
let currentPlan = null;
let billingMode = new URLSearchParams(window.location.search).get('mode') || 'monthly';
let planId = new URLSearchParams(window.location.search).get('plan') || 'starter';

// Global Identity verification
let session = null;
let supabaseClient = null;

async function verifyIdentity() {
    const supabaseUrl = window.INTEGRA_SETTINGS.SUPABASE_URL;
    const supabaseKey = window.INTEGRA_SETTINGS.SUPABASE_ANON_KEY;
    
    // Use global client from settings.js if available, otherwise create it
    if (window.supabaseClient) {
        supabaseClient = window.supabaseClient;
    } else {
        supabaseClient = supabase.createClient(supabaseUrl, supabaseKey);
    }
    
    const { data } = await supabaseClient.auth.getSession();
    session = data.session;
    
    if (!session) {
        window.location.href = 'index.html?error=auth_required';
        return;
    }

    // Initialize Stripe once identity is verified
    initializeStripe();
}

// Dynamic Initialization Node
async function initializeStripe() {
    const endpoints = [
        window.INTEGRA_SETTINGS.endpoint('/config'),
        ...window.INTEGRA_SETTINGS.API_FALLBACK_URLS.map(url => `${url}/config`)
    ];
    let publishableKey = null;

    for (let url of endpoints) {
        try {
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                publishableKey = data.publishableKey;
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
    const styleObj = {
        base: {
            color: '#ffffff',
            fontFamily: '"Space Mono", monospace',
            fontSize: '14px',
            '::placeholder': { color: 'rgba(255, 255, 255, 0.1)' },
            iconColor: '#22d3ee'
        },
        invalid: { color: '#ef4444' }
    };

    cardNumber = elements.create('cardNumber', { style: styleObj, showIcon: true });
    cardExpiry = elements.create('cardExpiry', { style: styleObj });
    cardCvc = elements.create('cardCvc', { style: styleObj });

    cardNumber.mount('#card-number-element');
    cardExpiry.mount('#card-expiry-element');
    cardCvc.mount('#card-cvc-element');
    
    cardNumber.on('ready', () => {
        const placeholder = document.querySelector('.placeholder-loading');
        if (placeholder) placeholder.remove();
    });
    
    setupCardAnimations();
    loadPlanData();
}

async function loadPlanData() {
    try {
        const response = await fetch('../../data/pricing.json');
        const data = await response.json();
        currentPlan = data.pricing_data.plans.find(p => p.id === planId);
        if (currentPlan) updatePriceDisplays();
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
    document.getElementById('billing-monthly')?.classList.toggle('active-billing', mode === 'monthly');
    document.getElementById('billing-yearly')?.classList.toggle('active-billing', mode === 'yearly');
}

// Initial UI Sync
selectBilling(billingMode);

// 3D Experience (Physics Engine)
const cardInner = document.getElementById('card-inner');
const cardContainer = document.querySelector('.card-container');

let isFlipped = false;

if (cardContainer && cardInner) {
    cardContainer.addEventListener('mousemove', (e) => {
        const rect = cardContainer.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        cardInner.style.transition = 'transform 0.1s linear';
        
        const baseY = isFlipped ? 180 : 0;
        cardInner.style.transform = `rotateX(${-y * 25}deg) rotateY(${baseY + (x * 25)}deg)`;
    });

    cardContainer.addEventListener('mouseleave', () => {
        cardInner.style.transition = 'transform 0.6s ease';
        cardInner.style.transform = isFlipped ? 'rotateY(180deg) rotateX(0deg)' : 'rotateY(0deg) rotateX(0deg)';
    });
}

// Identity Sync
const holderInput = document.getElementById('card-holder-name');
const holderDisplay = document.getElementById('card-holder-display');

if (holderInput && holderDisplay) {
    holderInput.addEventListener('input', (e) => {
        holderDisplay.textContent = e.target.value.toUpperCase() || 'JANE DOE';
    });
}

// Force Handle
const form = document.getElementById('payment-form');
const button = document.getElementById('submit-button');

if (form) {
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        button.disabled = true;
        button.textContent = 'AUTHENTICATING...';

        const { paymentMethod, error } = await stripe.createPaymentMethod({
            type: 'card',
            card: cardNumber,
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
}

async function processPayment(paymentMethodId) {
    if (!currentPlan) return;

    let amount = 0;
    if (currentPlan.monthly.price === 'Custom') {
        alert("Consultation required for Enterprise Tier.");
        button.disabled = false;
        button.textContent = 'Contact Sales';
        return;
    }

    if (billingMode === 'monthly') {
        amount = currentPlan.monthly.price * 100;
    } else {
        amount = currentPlan.yearly.price * 12 * 100;
    }

    try {
        const response = await fetch(window.INTEGRA_SETTINGS.endpoint('/create-payment-intent'), {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session?.access_token}`
            },
            body: JSON.stringify({ 
                payment_method_id: paymentMethodId, 
                amount: amount,
                plan_id: planId,
                billing_cycle: billingMode
            })
        });

        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            window.location.href = 'billing.html?status=success&plan=' + planId;
        } else {
            const errorMsg = result.detail || result.message || 'Unknown Protocol Error';
            alert('Security Link Severed: ' + errorMsg);
            button.disabled = false;
            button.textContent = 'Retry Handshake';
        }
    } catch (err) {
        console.error("=> System Critical Error: ", err);
        alert('Security Link Severed: Network timeout or connection lost.');
        button.disabled = false;
        button.textContent = 'Retry Handshake';
    }
}

// Start Verification
verifyIdentity();

// --- Neural Animation Logic ---
function setupCardAnimations() {
    const numberDisplay = document.getElementById('card-number-display');
    const expiryDisplay = document.getElementById('card-expiry-display');
    const cvcDisplay = document.getElementById('card-cvc-display');
    const cardInner = document.getElementById('card-inner');

    let scrambleInterval;
    const generateScramble = () => {
        let first4 = Math.floor(1000 + Math.random() * 9000);
        let last4 = Math.floor(1000 + Math.random() * 9000);
        return `${first4} **** **** ${last4}`;
    };

    cardNumber.on('change', (event) => {
        if (event.empty) {
            clearInterval(scrambleInterval);
            numberDisplay.textContent = '0000 0000 0000 0000';
            numberDisplay.classList.remove('text-cyan-400');
        } else if (event.complete) {
            clearInterval(scrambleInterval);
            // Simulate that it locked onto the encrypted state
            const fakeFirst = Math.floor(1000 + Math.random() * 9000);
            const fakeLast = Math.floor(1000 + Math.random() * 9000);
            numberDisplay.textContent = `${fakeFirst} **** **** ${fakeLast}`;
            numberDisplay.classList.add('text-cyan-400');
            numberDisplay.classList.add('shadow-[0_0_10px_rgba(34,211,238,0.5)]');
            setTimeout(() => {
                numberDisplay.classList.remove('shadow-[0_0_10px_rgba(34,211,238,0.5)]');
            }, 300);
        } else {
            // Typing...
            numberDisplay.classList.remove('text-cyan-400');
            clearInterval(scrambleInterval);
            scrambleInterval = setInterval(() => {
                numberDisplay.textContent = generateScramble();
            }, 50);
        }
    });

    const flipToBack = () => {
        isFlipped = true;
        if (cardInner) {
            cardInner.style.transition = 'transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            cardInner.style.transform = 'rotateY(180deg) rotateX(0deg)';
        }
    };

    const flipToFront = () => {
        isFlipped = false;
        if (cardInner) {
            cardInner.style.transition = 'transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            cardInner.style.transform = 'rotateY(0deg) rotateX(0deg)';
        }
    };

    cardExpiry.on('focus', flipToBack);
    cardExpiry.on('blur', flipToFront);
    cardCvc.on('focus', flipToBack);
    cardCvc.on('blur', flipToFront);

    cardExpiry.on('change', (e) => {
        if (e.empty) {
            expiryDisplay.textContent = 'MM/YY';
        } else if (e.complete) {
            expiryDisplay.textContent = '**/**';
            expiryDisplay.classList.add('text-cyan-400');
        } else {
            expiryDisplay.classList.remove('text-cyan-400');
            expiryDisplay.textContent = Math.random() > 0.5 ? 'M*/Y*' : '*M/*Y';
        }
    });

    cardCvc.on('change', (e) => {
        if (e.empty) {
            cvcDisplay.textContent = '•••';
        } else if (e.complete) {
            cvcDisplay.textContent = '***';
            cvcDisplay.classList.add('text-cyan-400');
        } else {
            cvcDisplay.classList.remove('text-cyan-400');
            cvcDisplay.textContent = Math.random() > 0.5 ? '*•*' : '•*•';
        }
    });
}


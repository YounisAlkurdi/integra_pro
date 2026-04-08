import { supabase } from './supabase-client.js';

document.addEventListener('DOMContentLoaded', () => {
    const googleBtn = document.getElementById('google-btn');
    const emailForm = document.getElementById('email-form');
    const userEmailInput = document.getElementById('user-email');
    const otpForm = document.getElementById('otp-form');
    const otpInput = document.getElementById('otp-input');
    const displayEmail = document.getElementById('display-email');
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const cursor = document.getElementById('cursor');

    // --- 1. Interactive Cursor ---
    if (cursor) {
        document.addEventListener('mousemove', (e) => {
            cursor.style.left = e.clientX + 'px';
            cursor.style.top = e.clientY + 'px';
        });

        document.body.addEventListener('mouseover', (e) => {
            if (['BUTTON', 'A', 'INPUT', 'SELECT'].includes(e.target.tagName)) {
                cursor.classList.add('hovering');
            }
        });

        document.body.addEventListener('mouseout', () => {
            cursor.classList.remove('hovering');
        });
    }

    // --- 2. Google Authentication ---
    googleBtn?.addEventListener('click', async () => {
        try {
            const { error } = await supabase.auth.signInWithOAuth({
                provider: 'google',
                    options: {
                        redirectTo: window.location.origin + '/dashboard.html',
                        queryParams: {
                            prompt: 'select_account',
                            access_type: 'offline'
                        },
                        flowType: 'pkce'
                    }
            });
            if (error) throw error;
        } catch (err) {
            console.error("Authentication Layer Error:", err.message);
            showToast(`Auth Failure: ${err.message}`, "error");
        }
    });

    // --- 3. Email OTP Initialization ---
    emailForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = userEmailInput.value;
        displayEmail.textContent = email;

        try {
            const { error } = await supabase.auth.signInWithOtp({
                email: email,
                options: {
                    shouldCreateUser: true
                }
            });

            if (error) throw error;

            showToast("Verification Pulse Sent: Check Inbox", "success");

            // Transition UI to OTP step
            step1.classList.add('opacity-0', 'scale-95');
            setTimeout(() => {
                step1.classList.add('hidden');
                step2.classList.remove('hidden');
                setTimeout(() => {
                    step2.classList.replace('opacity-0', 'opacity-100');
                    step2.classList.replace('scale-105', 'scale-100');
                }, 50);
            }, 500);

        } catch (err) {
            console.error("Verification Signal Interrupted:", err.message);
            showToast(`Signal Failed: ${err.message}`, "error");
        }
    });

    // --- 4. OTP Verification ---
    otpForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = userEmailInput.value;
        const token = otpInput.value;

        try {
            const { data, error } = await supabase.auth.verifyOtp({
                email,
                token,
                type: 'email'
            });

            if (error) throw error;

            if (data.session) {
                showToast("Identity Confirmed: Access Granted", "success");
                setTimeout(() => window.location.href = 'dashboard.html', 1500);
            }
        } catch (err) {
            console.error("Neural Verification Failed:", err.message);
            showToast("Access Denied: Invalid Code", "error");
        }
    });
});

/**
 * Aesthetic Toast Notification System
 */
function showToast(msg, type = "success") { 
    const container = document.getElementById('toast-container') || createToastContainer(); 
    const toast = document.createElement('div'); 
    
    const colors = {
        success: 'border-cyan-400 text-cyan-400 bg-cyan-400/5',
        error: 'border-red-500 text-red-500 bg-red-400/5',
        system: 'border-white/20 text-white bg-white/5'
    };

    toast.className = `px-6 py-4 border rounded-xl backdrop-blur-xl animate-in slide-in-from-right-10 flex items-center gap-4 text-[10px] font-mono uppercase tracking-[0.2em] mb-3 pointer-events-auto shadow-2xl ${colors[type] || colors.success}`; 
    toast.innerHTML = `<div class="w-1.5 h-1.5 rounded-full bg-current ${type === 'success' ? 'animate-pulse' : ''}"></div> ${msg}`; 
    
    container.appendChild(toast); 
    
    setTimeout(() => {
        toast.classList.add('animate-out', 'fade-out', 'slide-out-to-right-10');
        setTimeout(() => toast.remove(), 500);
    }, 4000);
} 

function createToastContainer() { 
    const div = document.createElement('div'); 
    div.id = 'toast-container'; 
    div.className = 'fixed bottom-10 right-10 z-[100] flex flex-col gap-3'; 
    document.body.appendChild(div); 
    return div; 
}

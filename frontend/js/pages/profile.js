// Integra Profile Management
import { supabase } from '../core/supabase-client.js';

document.addEventListener("DOMContentLoaded", async () => {
    if (window.lucide) lucide.createIcons();

    // 1. Fetch Identity from Supabase
    try {
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
            window.location.href = 'index.html';
            return;
        }

        // 2. Map Data to UI
        const nameEl = document.getElementById('p-name');
        const emailEl = document.getElementById('p-email');
        const idEl = document.getElementById('p-id');
        const avatarEl = document.getElementById('p-avatar');
        const providerEl = document.getElementById('p-provider');

        const metadata = user.user_metadata || {};

        if (nameEl) nameEl.textContent = metadata.full_name || 'Anonymous Subject';
        if (emailEl) emailEl.textContent = user.email;
        if (idEl) idEl.textContent = user.id;
        if (providerEl) providerEl.textContent = `${user.app_metadata.provider} Security Protocol`;

        if (avatarEl && metadata.avatar_url) {
            avatarEl.innerHTML = `<img src="${metadata.avatar_url}" class="w-full h-full object-cover">`;
        } else if (avatarEl) {
            const initials = metadata.full_name?.split(' ').map(n => n[0]).join('').toUpperCase() || user.email[0].toUpperCase();
            avatarEl.innerHTML = `<div class="text-4xl font-black italic text-cyan-400/20">${initials}</div>`;
        }

    } catch (e) {
        console.error("Identity Synchronization Failed:", e);
    }

    // Utility: Copy User ID
    window.copyID = () => {
        const id = document.getElementById('p-id').textContent;
        navigator.clipboard.writeText(id).then(() => {
            showToast("ID Copied Securely", "info");
        });
    };
});

// Toast Helper
function showToast(msg, type = "info") { 
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-10 right-10 z-[100] flex flex-col gap-3';
        document.body.appendChild(container);
    }
    
    const colors = {
        success: 'border-cyan-400 text-cyan-400 bg-cyan-400/5',
        error: 'border-red-500 text-red-500 bg-red-400/5',
        system: 'border-white/20 text-white bg-white/5',
        info: 'border-white/40 text-white/80 bg-white/5'
    };

    const toast = document.createElement('div'); 
    toast.className = `px-6 py-4 border rounded-xl backdrop-blur-xl animate-in slide-in-from-right-10 flex items-center gap-4 text-[10px] font-mono uppercase tracking-[0.2em] mb-3 pointer-events-auto shadow-2xl ${colors[type]}`; 
    toast.innerHTML = `<div class="w-1.5 h-1.5 rounded-full bg-current"></div> ${msg}`; 
    
    container.appendChild(toast); 
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.5s ease';
        setTimeout(() => toast.remove(), 500);
    }, 2500);
}

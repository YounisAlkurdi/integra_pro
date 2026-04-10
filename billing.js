import { supabase } from './supabase-client.js';

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize Icons
    lucide.createIcons();

    // Check for success status
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('status') === 'success') {
        showSuccessProtocol();
    }

    // Export close function to window
    window.closeSuccessOverlay = () => {
        document.getElementById('success-overlay').classList.remove('active');
        // Clean URL
        window.history.replaceState({}, document.title, window.location.pathname);
    };

    // 1. Identity Verification
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
        window.location.href = 'index.html';
        return;
    }

    const user = session.user;
    console.log("Financial Node Auth: Verified for", user.email);

    // 2. Fetch Invoices
    const { data: invoices, error } = await supabase
        .from('invoices')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });

    if (error) {
        console.error("Failed to fetch ledger:", error);
        renderError();
        return;
    }

    renderInvoices(invoices);
    renderStats(invoices);

    // Update 'Active Protocol' text if subscription found
    const { data: subData } = await supabase
        .from('subscriptions')
        .select('plan_id')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false })
        .limit(1);
    
    if (subData && subData.length > 0) {
        const protocolEl = document.querySelector('p.text-lg.font-black.tracking-tighter.text-white.uppercase.italic');
        if (protocolEl) {
            protocolEl.textContent = getFriendlyPlanName(subData[0].plan_id);
        }
    }
});

function showSuccessProtocol() {
    const overlay = document.getElementById('success-overlay');
    const bar = document.getElementById('neural-bar');
    const status = document.getElementById('success-status');

    if (!overlay) return;
    overlay.classList.add('active');
    
    setTimeout(() => {
        if (bar) bar.style.width = '100%';
        setTimeout(() => {
            if (status) status.textContent = 'Neural Ledger Synchronized. Access Granted.';
        }, 2000);
    }, 500);
}

function renderStats(invoices) {
    if (!invoices || invoices.length === 0) return;

    const total = invoices.reduce((sum, inv) => sum + inv.amount, 0);
    const last = invoices[0].amount;
    
    // Simple logic for next billing (30 days from last)
    const lastDate = new Date(invoices[0].created_at);
    const nextDate = new Date(lastDate.getTime() + (30 * 24 * 60 * 60 * 1000));

    document.getElementById('stat-last-amount').innerText = `$${(last / 100).toFixed(2)}`;
    document.getElementById('stat-total-invested').innerText = `$${(total / 100).toFixed(2)}`;
    document.getElementById('stat-next-billing').innerText = nextDate.toLocaleDateString();
}

function renderInvoices(invoices) {
    const container = document.getElementById('invoices-list');
    
    if (!invoices || invoices.length === 0) {
        container.innerHTML = `
            <div class="p-20 text-center opacity-30">
                <i data-lucide="ghost" class="w-10 h-10 mx-auto mb-4 text-white/20"></i>
                <p class="text-[10px] font-mono uppercase tracking-[0.3em]">No transaction records found</p>
                <p class="text-[9px] text-white/40 mt-2 font-mono">Subscribe to the Pro Protocol to initiate ledger entries.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    container.innerHTML = invoices.map(inv => `
        <div class="p-8 hover:bg-white/[0.02] transition-colors group flex items-center justify-between">
            <div class="flex items-center gap-6">
                <div class="w-12 h-12 rounded-xl bg-white/5 border border-white/5 flex items-center justify-center text-cyan-400 group-hover:border-cyan-400/30 transition-all">
                    <i data-lucide="receipt" class="w-5 h-5"></i>
                </div>
                <div>
                    <h3 class="text-sm font-bold uppercase tracking-tight italic mb-1">${getFriendlyPlanName(inv.plan_id)}</h3>
                    <p class="text-[9px] font-mono text-white/30 uppercase tracking-widest">${new Date(inv.created_at).toLocaleDateString()} • REF: ${inv.id.split('-')[0]}</p>
                </div>
            </div>
            
            <div class="flex items-center gap-12">
                <div class="text-right">
                    <p class="text-lg font-black tracking-tighter">$${(inv.amount / 100).toFixed(2)}</p>
                    <p class="text-[8px] font-mono text-cyan-400/60 uppercase tracking-widest">Transaction Successful</p>
                </div>
                <div class="flex items-center gap-2 px-4 py-2 bg-cyan-400/10 border border-cyan-400/20 rounded-lg">
                    <div class="w-1.5 h-1.5 bg-cyan-400 rounded-full"></div>
                    <span class="text-[9px] font-mono font-bold text-cyan-400 uppercase tracking-widest">PAID</span>
                </div>
                <button class="p-2 hover:bg-white/10 rounded-lg transition-all opacity-0 group-hover:opacity-100">
                    <i data-lucide="download" class="w-4 h-4 text-white/40"></i>
                </button>
            </div>
        </div>
    `).join('');

    lucide.createIcons();
}

function renderError() {
    const container = document.getElementById('invoices-list');
    container.innerHTML = `
        <div class="p-20 text-center text-red-400">
            <i data-lucide="alert-octagon" class="w-12 h-12 mx-auto mb-4"></i>
            <p class="text-xs font-mono uppercase tracking-widest">Ledger Sync Error</p>
        </div>
    `;
}

function getFriendlyPlanName(plan_id) {
    const names = {
        'free': 'Neural Bridge Protocol',
        'starter': 'System Core Protocol',
        'professional': 'Neural Nexus Protocol',
        'nexus': 'Nexus Core Protocol'
    };
    return names[plan_id] || `${plan_id.toUpperCase()} PROTOCOL`;
}

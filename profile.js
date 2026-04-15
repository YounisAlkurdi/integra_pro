// Integra Profile Management
import { supabase } from './supabase-client.js';

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

    // --- NEW: Neural Matrix Logic ---
    
    // Auto-populate MCP Config with real credentials
    const mcpPre = document.getElementById('mcp-config-json');
    if (mcpPre) {
        const sbUrl = supabase.supabaseUrl;
        const sbKey = supabase.supabaseKey;
        mcpPre.textContent = JSON.stringify({
            "mcpServers": {
                "integra": {
                    "command": "python",
                    "args": ["C:/PATH/TO/PROJECT/integra_mcp.py"],
                    "env": {
                        "SUPABASE_URL": sbUrl,
                        "SUPABASE_ANON_KEY": sbKey
                    }
                }
            }
        }, null, 2);
    }

    // Utility: Copy Neural Hub Config
    window.copyConfig = () => {
        const configText = document.getElementById('mcp-config-json').textContent;
        navigator.clipboard.writeText(configText).then(() => {
            showToast("MCP CONFIG COPIED", "success");
        });
    };

    // Load Existing External Matrix Links
    window.loadExternalMCPs = async () => {
        const { data: { user } } = await supabase.auth.getUser();
        if(!user) return;

        const { data, error } = await supabase
            .from('external_mcps')
            .select('*')
            .eq('user_id', user.id)
            .order('created_at', { ascending: false });

        const listEl = document.getElementById('external-mcp-list');
        if (error || !data || data.length === 0) {
            listEl.innerHTML = `
                <div class="p-6 bg-white/5 border border-dashed border-white/10 rounded-2xl flex flex-col items-center justify-center gap-3 opacity-50 col-span-full">
                    <i data-lucide="plus-circle" class="w-6 h-6"></i>
                    <span class="text-[8px] font-mono uppercase tracking-widest">No External Links Linked</span>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            return;
        }

        listEl.innerHTML = data.map(mcp => `
            <div class="p-6 bg-white/5 border border-white/10 rounded-2xl group relative overflow-hidden">
                <div class="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div class="relative z-10">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-[8px] font-black uppercase tracking-widest text-purple-400">${mcp.mcp_name}</span>
                        <span class="text-[7px] font-mono text-white/20 uppercase tracking-widest">${mcp.mcp_type}</span>
                    </div>
                    <code class="text-[10px] font-mono text-white/40 block truncate mb-4">${JSON.stringify(mcp.mcp_config)}</code>
                    <button onclick="unlinkMCP('${mcp.id}')" class="text-[8px] font-black uppercase tracking-widest text-red-400/50 hover:text-red-400 transition-all">Sever Link</button>
                </div>
            </div>
        `).join('');
        if (window.lucide) lucide.createIcons();
    };

    // --- ADAPTIVE NEURAL INTERFACE: PROVIDER SELECTOR ---
    let currentProvider = 'custom';

    window.selectProvider = (type) => {
        currentProvider = type;
        const configLabel = document.getElementById('config-label');
        const configArea = document.getElementById('mcp-config');
        const nameContainer = document.getElementById('field-name-container');
        
        // Reset Card UI
        document.querySelectorAll('.provider-card').forEach(card => {
            card.classList.remove('border-purple-400/50', 'bg-purple-500/10');
            card.querySelectorAll('i, span').forEach(el => el.classList.replace('text-purple-400', 'text-white/30'));
        });

        // Highlight Selected Card
        const btn = document.getElementById(`btn-${type}`);
        btn.classList.add('border-purple-400/50', 'bg-purple-500/10');
        btn.querySelectorAll('i, span').forEach(el => el.classList.replace('text-white/30', 'text-purple-400'));

        // Adapt UI based on Provider
        if (type === 'stripe') {
            configLabel.textContent = "Stripe Secret Key (sk_live_...)";
            configArea.placeholder = "Enter your secret key here...";
            configArea.value = "";
            configArea.style.height = "60px";
            nameContainer.style.display = "none";
        } else if (type === 'slack') {
            configLabel.textContent = "Slack Bot Token (xoxb-...)";
            configArea.placeholder = "Enter your bot token here...";
            configArea.value = "";
            configArea.style.height = "60px";
            nameContainer.style.display = "none";
        } else {
            configLabel.textContent = "JSON Credentials Matrix";
            configArea.placeholder = '{ "key": "value" }';
            configArea.style.height = "128px";
            nameContainer.style.display = "block";
        }
    };

    // Updated: Register New External Matrix Link
    window.linkNewMCP = async () => {
        let name = document.getElementById('mcp-name').value;
        const configRaw = document.getElementById('mcp-config').value;

        if (!configRaw) {
            showToast("Protocol Failed: No Data Clusters Found", "error");
            return;
        }

        let configObj = {};
        let finalType = currentProvider;

        try {
            if (currentProvider === 'stripe') {
                name = 'Stripe Matrix';
                configObj = { "stripe_secret_key": configRaw };
                finalType = 'Finance';
            } else if (currentProvider === 'slack') {
                name = 'Slack Transmitter';
                configObj = { "slack_bot_token": configRaw };
                finalType = 'Communication';
            } else {
                configObj = JSON.parse(configRaw);
                if (!name) name = "Custom Link";
            }

            const { data: { user } } = await supabase.auth.getUser();

            const { error } = await supabase.from('external_mcps').insert({
                user_id: user.id,
                mcp_name: name,
                mcp_type: finalType,
                mcp_config: configObj
            });

            if (error) throw error;

            showToast("NEURAL LINK ESTABLISHED", "success");
            loadExternalMCPs();

        } catch (e) {
            showToast("Matrix Configuration Error: Invalid Data", "error");
        }
    };

    // Sever Link
    window.unlinkMCP = async (id) => {
        const { error } = await supabase.from('external_mcps').delete().eq('id', id);
        if (error) {
            showToast("Severing Failed", "error");
        } else {
            showToast("Link Severed Successfully", "system");
            loadExternalMCPs();
        }
    };

    // Utility: Copy User ID
    window.copyID = () => {
        const id = document.getElementById('p-id').textContent;
        navigator.clipboard.writeText(id).then(() => {
            showToast("ID Copied Securely", "info");
        });
    };

    // Initial Load
    loadExternalMCPs();
});

// --- NEURAL PRESETS: TEMPLATE ENGINE ---
window.fillTemplate = (type) => {
    const configArea = document.getElementById('mcp-config');
    const nameInput = document.getElementById('mcp-name');
    const typeInput = document.getElementById('mcp-type');

    const templates = {
        'stripe': {
            name: 'stripe-server',
            type: 'Finance',
            json: {
                "stripe_secret_key": "YOUR_SK_KEY_HERE",
                "description": "Financial Data Node"
            }
        },
        'slack': {
            name: 'slack-transmitter',
            type: 'Communication',
            json: {
                "slack_bot_token": "YOUR_TOKEN_HERE",
                "default_channel": "general"
            }
        },
        'clear': {
            name: '',
            type: '',
            json: ''
        }
    };

    const t = templates[type];
    if (t) {
        nameInput.value = t.name;
        typeInput.value = t.type;
        configArea.value = t.json ? JSON.stringify(t.json, null, 2) : '';
    }
};

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

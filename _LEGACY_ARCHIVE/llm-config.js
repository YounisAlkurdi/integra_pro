/**
 * LLM Config JS — Integra
 * يدير صفحة إعدادات العقل التحليلي
 * نسخة مستقرة 100% بدون تعقيدات الموديولات
 */

const STORAGE_KEY = 'INTEGRA_LLM_CONFIG';

// ─── Load saved config on init ────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    const saved = getSavedConfig();

    // System Prompt
    if (saved.systemPrompt) {
        const el = document.getElementById('system-prompt');
        if (el) el.value = saved.systemPrompt;
    }

    // Temperature
    const temp = saved.temperature ?? 0.1;
    const slider = document.getElementById('llm-temp');
    if (slider) {
        slider.value = temp;
        updateTempDisplay(temp);
    }

    // Source
    const source = saved.source || 'api';
    const sourceRadio = document.querySelector(`input[name="source"][value="${source}"]`);
    if (sourceRadio) sourceRadio.checked = true;
    switchSource(source);

    // Provider
    const provider = saved.apiProvider || 'openai';
    const providerRadio = document.querySelector(`input[name="provider"][value="${provider}"]`);
    if (providerRadio) providerRadio.checked = true;
    
    // تأكيد تعبئة القائمة
    populateModels(provider);

    // API Model (Select the saved model after populating)
    if (saved.apiModel) {
        setTimeout(() => {
            const sel = document.getElementById('api-model');
            if (sel) sel.value = saved.apiModel;
        }, 100);
    }

    // API Key
    if (saved.apiKey) {
        const keyInp = document.getElementById('api-key');
        if (keyInp) keyInp.value = saved.apiKey;
    }

    // Local
    if (saved.localUrl) document.getElementById('local-url').value = saved.localUrl;
    if (saved.localModel) document.getElementById('local-model').value = saved.localModel;

    // HF
    populateHFModels();
    if (saved.hfModel) {
        setTimeout(() => { 
            const hfSel = document.getElementById('hf-model');
            if (hfSel) hfSel.value = saved.hfModel; 
        }, 100);
    }
    if (saved.hfToken) document.getElementById('hf-token').value = saved.hfToken;
});

// ─── Populate HF models ───────────────────────────────────────────────
function populateHFModels() {
    const sel = document.getElementById('hf-model');
    if (!sel) return;
    sel.innerHTML = '';
    (window.HF_MODELS || []).forEach(m => {
        const opt = document.createElement('option');
        opt.value = m; opt.textContent = m;
        sel.appendChild(opt);
    });
}

// ─── Populate API models based on provider ────────────────────────────
function populateModels(provider) {
    const sel = document.getElementById('api-model');
    if (!sel) return;
    sel.innerHTML = '';
    
    // التأكد من وجود البيانات في window
    const allModels = window.PROVIDER_MODELS || {};
    const models = allModels[provider] || [];
    
    if (models.length === 0) {
        console.warn("No models found for provider:", provider);
    }

    models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m; opt.textContent = m;
        sel.appendChild(opt);
    });
}

// ─── Source switch logic ───────────────────────────────────────────────
function switchSource(source) {
    const apiS = document.getElementById('api-section');
    const locS = document.getElementById('local-section');
    const hfS = document.getElementById('hf-section');
    if (apiS) apiS.classList.toggle('hidden', source !== 'api');
    if (locS) locS.classList.toggle('hidden', source !== 'local');
    if (hfS) hfS.classList.toggle('hidden', source !== 'hf');
}

// ─── Temperature display ───────────────────────────────────────────────
function updateTempDisplay(val) {
    const disp = document.getElementById('temp-display');
    if (disp) disp.textContent = parseFloat(val).toFixed(2);
}

// ─── Eye toggle for API key ────────────────────────────────────────────
function toggleApiKey() {
    const inp = document.getElementById('api-key');
    const icon = document.getElementById('eye-icon');
    if (!inp || !icon) return;
    
    if (inp.type === 'password') {
        inp.type = 'text';
        icon.setAttribute('data-lucide', 'eye-off');
    } else {
        inp.type = 'password';
        icon.setAttribute('data-lucide', 'eye');
    }
    if (window.lucide) lucide.createIcons();
}

// ─── Save config ───────────────────────────────────────────────────────
async function saveConfig() {
    const source = document.querySelector('input[name="source"]:checked')?.value || 'api';
    const provider = document.querySelector('input[name="provider"]:checked')?.value || 'openai';

    const config = {
        systemPrompt: document.getElementById('system-prompt').value.trim(),
        temperature: parseFloat(document.getElementById('llm-temp').value),
        source,
        apiProvider: provider,
        apiModel: document.getElementById('api-model').value,
        apiKey: document.getElementById('api-key').value.trim(),
        localUrl: document.getElementById('local-url').value.trim(),
        localModel: document.getElementById('local-model').value.trim(),
        hfModel: document.getElementById('hf-model').value,
        hfToken: document.getElementById('hf-token').value.trim(),
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    
    // Sync to Supabase if available globally
    if (window.supabase) {
        await syncToCloud(config);
    }
    
    showToast();
}

async function syncToCloud(config) {
    try {
        const { data: { session } } = await window.supabase.auth.getSession();
        if (!session) return;
        
        await window.supabase
            .from('user_settings')
            .upsert({
                user_id: session.user.id,
                llm_api_key: config.apiKey,
                llm_provider: config.apiProvider,
                llm_model: config.apiModel,
                system_prompt_override: config.systemPrompt,
                updated_at: new Date().toISOString()
            });
    } catch (e) {
        console.error("[Cloud Sync] Error:", e);
    }
}

function getSavedConfig() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch { return {}; }
}

function showToast() {
    const t = document.getElementById('toast');
    if (!t) return;
    t.classList.remove('translate-y-20', 'opacity-0');
    t.classList.add('translate-y-0', 'opacity-100');
    setTimeout(() => {
        t.classList.add('translate-y-20', 'opacity-0');
        t.classList.remove('translate-y-0', 'opacity-100');
    }, 3000);
}

// ─── Event listeners ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const tempInp = document.getElementById('llm-temp');
    if (tempInp) tempInp.addEventListener('input', e => updateTempDisplay(e.target.value));

    document.querySelectorAll('input[name="source"]').forEach(radio => {
        radio.addEventListener('change', e => switchSource(e.target.value));
    });

    document.querySelectorAll('input[name="provider"]').forEach(radio => {
        radio.addEventListener('change', e => populateModels(e.target.value));
    });
});

// Expose functions
window.saveConfig = saveConfig;
window.toggleApiKey = toggleApiKey;
window.populateModels = populateModels;
window.getLLMConfig = getSavedConfig;

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

    // Provider (API Section)
    const provider = saved.apiProvider || 'openai';
    const providerRadio = document.querySelector(`input[name="provider"][value="${provider}"]`);
    if (providerRadio) providerRadio.checked = true;
    
    // API Models
    populateModels(provider);

    if (saved.apiModel) {
        setTimeout(() => {
            const sel = document.getElementById('api-model');
            if (sel) sel.value = saved.apiModel;
        }, 100);
    }

    if (saved.apiKey) {
        const keyInp = document.getElementById('api-key');
        if (keyInp) keyInp.value = saved.apiKey;
    }

    // Local
    if (saved.localUrl) document.getElementById('local-url').value = saved.localUrl;
    if (saved.localModel) document.getElementById('local-model').value = saved.localModel;

    // Neural Matrix (Universal Provider)
    if (saved.hfProviderType) {
        const hfProv = document.getElementById('hf-provider-type');
        if (hfProv) {
            hfProv.value = saved.hfProviderType;
            populateNeuralModels(saved.hfProviderType);
        }
    } else {
        populateNeuralModels('kie'); // Default
    }

    if (saved.hfModelCustom) {
        setTimeout(() => {
            const hfMod = document.getElementById('hf-model-custom');
            if (hfMod) hfMod.value = saved.hfModelCustom;
        }, 150);
    }
    if (saved.hfTokenCustom) {
        const hfTok = document.getElementById('hf-token-custom');
        if (hfTok) hfTok.value = saved.hfTokenCustom;
    }
});

// ─── Populate Neural Matrix models ────────────────────────────────────
function populateNeuralModels(provider) {
    const sel = document.getElementById('hf-model-custom');
    if (!sel) return;
    sel.innerHTML = '';
    
    const allModels = window.PROVIDER_MODELS || {};
    const models = allModels[provider] || [];
    
    models.forEach(m => {
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
    
    const allModels = window.PROVIDER_MODELS || {};
    const models = allModels[provider] || [];
    
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
    const track = document.getElementById('temp-track');
    const thumb = document.getElementById('temp-thumb');
    
    if (disp) disp.textContent = parseFloat(val).toFixed(2);
    if (track) track.style.width = (val * 100) + '%';
    if (thumb) thumb.style.left = (val * 100) + '%';
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
        // API Cloud
        apiProvider: provider,
        apiModel: document.getElementById('api-model').value,
        apiKey: document.getElementById('api-key').value.trim(),
        // Local
        localUrl: document.getElementById('local-url').value.trim(),
        localModel: document.getElementById('local-model').value.trim(),
        // Neural Matrix (Universal)
        hfProviderType: document.getElementById('hf-provider-type').value,
        hfModelCustom: document.getElementById('hf-model-custom').value.trim(),
        hfTokenCustom: document.getElementById('hf-token-custom').value.trim(),
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    
    // Sync to Supabase
    if (window.supabase) {
        await syncToCloud(config);
    }
    
    showToast();
}

async function syncToCloud(config) {
    try {
        const { data: { session } } = await window.supabase.auth.getSession();
        if (!session) return;
        
        // We sync the active model based on source
        let activeKey = config.apiKey;
        let activeProvider = config.apiProvider;
        let activeModel = config.apiModel;

        if (config.source === 'hf') {
            activeKey = config.hfTokenCustom;
            activeProvider = config.hfProviderType;
            activeModel = config.hfModelCustom;
        } else if (config.source === 'local') {
            activeKey = 'LOCAL';
            activeProvider = 'ollama';
            activeModel = config.localModel;
        }

        await window.supabase
            .from('user_settings')
            .upsert({
                user_id: session.user.id,
                llm_api_key: activeKey,
                llm_provider: activeProvider,
                llm_model: activeModel,
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

    const hfProvSelect = document.getElementById('hf-provider-type');
    if (hfProvSelect) {
        hfProvSelect.addEventListener('change', e => populateNeuralModels(e.target.value));
    }
});

// Expose functions
window.saveConfig = saveConfig;
window.toggleApiKey = toggleApiKey;
window.populateModels = populateModels;
window.getLLMConfig = getSavedConfig;


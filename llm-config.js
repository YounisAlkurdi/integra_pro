/**
 * LLM Config JS — Integra
 * يدير صفحة إعدادات العقل التحليلي
 * يستخدم models.config.js (مأخوذ من D:\Voiser\tts\frontend\js\models.config.js)
 */

const STORAGE_KEY = 'INTEGRA_LLM_CONFIG';

// ─── Load saved config on init ────────────────────────────────────────
(function init() {
    const saved = getSavedConfig();

    // System Prompt
    if (saved.systemPrompt) {
        document.getElementById('system-prompt').value = saved.systemPrompt;
    }

    // Temperature
    const temp = saved.temperature ?? 0.1;
    const slider = document.getElementById('llm-temp');
    slider.value = temp;
    updateTempDisplay(temp);

    // Source
    const source = saved.source || 'api';
    const sourceRadio = document.querySelector(`input[name="source"][value="${source}"]`);
    if (sourceRadio) sourceRadio.checked = true;
    switchSource(source);

    // Provider
    const provider = saved.apiProvider || 'openai';
    const providerRadio = document.querySelector(`input[name="provider"][value="${provider}"]`);
    if (providerRadio) providerRadio.checked = true;
    populateModels(provider);

    // API Model
    if (saved.apiModel) {
        setTimeout(() => {
            const sel = document.getElementById('api-model');
            sel.value = saved.apiModel;
        }, 50);
    }

    // API Key
    if (saved.apiKey) document.getElementById('api-key').value = saved.apiKey;

    // Local
    if (saved.localUrl) document.getElementById('local-url').value = saved.localUrl;
    if (saved.localModel) document.getElementById('local-model').value = saved.localModel;

    // HF
    populateHFModels();
    if (saved.hfModel) {
        setTimeout(() => { document.getElementById('hf-model').value = saved.hfModel; }, 50);
    }
    if (saved.hfToken) document.getElementById('hf-token').value = saved.hfToken;
})();

// ─── Populate HF models from models.config.js ─────────────────────────
function populateHFModels() {
    const sel = document.getElementById('hf-model');
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
    sel.innerHTML = '';
    const models = (window.PROVIDER_MODELS || {})[provider] || [];
    models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m; opt.textContent = m;
        sel.appendChild(opt);
    });
}

// ─── Source switch logic ───────────────────────────────────────────────
function switchSource(source) {
    document.getElementById('api-section').classList.toggle('hidden', source !== 'api');
    document.getElementById('local-section').classList.toggle('hidden', source !== 'local');
    document.getElementById('hf-section').classList.toggle('hidden', source !== 'hf');
}

// ─── Temperature display ───────────────────────────────────────────────
function updateTempDisplay(val) {
    document.getElementById('temp-display').textContent = parseFloat(val).toFixed(2);
}

// ─── Eye toggle for API key ────────────────────────────────────────────
function toggleApiKey() {
    const inp = document.getElementById('api-key');
    const icon = document.getElementById('eye-icon');
    if (inp.type === 'password') {
        inp.type = 'text';
        icon.setAttribute('data-lucide', 'eye-off');
    } else {
        inp.type = 'password';
        icon.setAttribute('data-lucide', 'eye');
    }
    lucide.createIcons();
}

// ─── Save config ───────────────────────────────────────────────────────
function saveConfig() {
    const source = document.querySelector('input[name="source"]:checked')?.value || 'api';
    const provider = document.querySelector('input[name="provider"]:checked')?.value || 'openai';

    const config = {
        systemPrompt: document.getElementById('system-prompt').value.trim(),
        temperature: parseFloat(document.getElementById('llm-temp').value),
        source,
        // API
        apiProvider: provider,
        apiModel: document.getElementById('api-model').value,
        apiKey: document.getElementById('api-key').value.trim(),
        // Local
        localUrl: document.getElementById('local-url').value.trim(),
        localModel: document.getElementById('local-model').value.trim(),
        // HF
        hfModel: document.getElementById('hf-model').value,
        hfToken: document.getElementById('hf-token').value.trim(),
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    showToast();
}

function getSavedConfig() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch { return {}; }
}

// ─── Toast notification ────────────────────────────────────────────────
function showToast() {
    const t = document.getElementById('toast');
    t.classList.remove('translate-y-20', 'opacity-0');
    t.classList.add('translate-y-0', 'opacity-100');
    setTimeout(() => {
        t.classList.add('translate-y-20', 'opacity-0');
        t.classList.remove('translate-y-0', 'opacity-100');
    }, 3000);
}

// ─── Event listeners ──────────────────────────────────────────────────
document.getElementById('llm-temp').addEventListener('input', e => updateTempDisplay(e.target.value));

document.querySelectorAll('input[name="source"]').forEach(radio => {
    radio.addEventListener('change', e => switchSource(e.target.value));
});

document.querySelectorAll('input[name="provider"]').forEach(radio => {
    radio.addEventListener('change', e => populateModels(e.target.value));
});

// ─── Export config for other pages ────────────────────────────────────
window.getLLMConfig = getSavedConfig;

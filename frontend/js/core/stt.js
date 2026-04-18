/**
 * stt.js — Speech-to-Text Engine v3
 *
 * Uses Web Speech API (SpeechRecognition).
 * Fires DOM events:
 *   stt:final   → { text, identity, name }
 *   stt:interim → { text, identity, name }
 *
 * Fixes vs v2:
 *  - Exponential backoff on restart (300ms → 600ms → 1200ms → ... → 5000ms max)
 *    prevents hot-loop when browser's STT service rejects repeated restarts.
 *  - Retry counter resets on successful speech result (not just on start()).
 *  - Noise gate: ignores result strings under 2 characters (button presses, noise).
 *  - setMuted() now properly resets backoff so unmute is instant.
 */

const STTEngine = (() => {

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    let recognition    = null;
    let currentSession = null;   // { identity, name }
    let running        = false;
    let muted          = false;
    let restartTimer   = null;
    let retryCount     = 0;      // For exponential backoff
    const MAX_DELAY_MS = 5000;   // Cap at 5 seconds between restart attempts
    const BASE_DELAY_MS = 300;

    function isSupported() {
        return !!SpeechRecognition;
    }

    function dispatch(eventName, text) {
        if (!currentSession) return;
        window.dispatchEvent(new CustomEvent(eventName, {
            detail: {
                text,
                identity: currentSession.identity,
                name:     currentSession.name,
            }
        }));
    }

    /** Calculate backoff delay: 300 * 2^retryCount, capped at MAX_DELAY_MS */
    function getBackoffDelay() {
        return Math.min(BASE_DELAY_MS * Math.pow(2, retryCount), MAX_DELAY_MS);
    }

    function buildRecognition(lang) {
        if (!SpeechRecognition) return null;

        const r = new SpeechRecognition();
        r.continuous       = true;   // keep listening across silences
        r.interimResults   = true;   // fire partial results immediately
        r.maxAlternatives  = 1;      // single best match

        // Support Arabic + English code-switching (common in interviews)
        r.lang = lang;

        r.onresult = (event) => {
            if (muted) return;

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                const text   = result[0].transcript.trim();

                // Noise gate: skip empty or single-char noise (clicks, pops)
                if (text.length < 2) continue;

                if (result.isFinal) {
                    retryCount = 0; // Reset backoff — we got real speech
                    dispatch('stt:final', text);
                } else {
                    dispatch('stt:interim', text);
                }
            }
        };

        r.onerror = (event) => {
            // 'no-speech' and 'aborted' are normal — retry with backoff
            if (event.error === 'no-speech' || event.error === 'aborted') {
                scheduleRestart();
                return;
            }
            // 'not-allowed': user blocked mic — don't retry
            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                console.warn('[STT] Mic permission denied. STT disabled.');
                running = false;
                return;
            }
            // Other errors: retry with backoff
            console.warn('[STT] Error:', event.error);
            retryCount++;
            scheduleRestart();
        };

        r.onend = () => {
            // SpeechRecognition stops automatically on silence — always restart
            if (running && !muted) {
                scheduleRestart();
            }
        };

        return r;
    }

    function scheduleRestart() {
        if (!running || muted) return;
        clearTimeout(restartTimer);
        const delay = getBackoffDelay();
        restartTimer = setTimeout(() => {
            if (running && !muted && recognition) {
                try {
                    recognition.start();
                } catch (_) {
                    // Already running or aborted — retry next cycle
                    retryCount++;
                    scheduleRestart();
                }
            }
        }, delay);
    }

    function start({ identity, name, lang = 'ar-SA' } = {}) {
        if (!SpeechRecognition) return;
        stop(); // Clean up any previous session

        currentSession = { identity, name };
        muted          = false;
        running        = true;
        retryCount     = 0; // Reset backoff on fresh start

        recognition = buildRecognition(lang);
        try {
            recognition.start();
        } catch (e) {
            console.warn('[STT] Could not start:', e);
            scheduleRestart();
        }
    }

    function stop() {
        running        = false;
        muted          = false;
        currentSession = null;
        retryCount     = 0;
        clearTimeout(restartTimer);

        if (recognition) {
            try { recognition.abort(); } catch (_) {}
            recognition = null;
        }
    }

    // Mute pauses recognition without destroying state.
    // When unmuted, recognition resumes immediately (no backoff delay).
    function setMuted(isMuted) {
        muted = isMuted;
        if (!recognition || !running) return;

        if (isMuted) {
            try { recognition.abort(); } catch (_) {}
        } else {
            retryCount = 0; // Instant restart after unmute — no backoff
            scheduleRestart();
        }
    }

    function isActive() { return running && !muted; }

    return { start, stop, setMuted, isSupported, isActive };

})();

window.STTEngine = STTEngine;

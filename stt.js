/**
 * stt.js — Browser Speech-to-Text Engine
 * Uses the native Web Speech API (Chrome/Edge).
 * Fires custom DOM events so LiveKit and UI layers stay decoupled.
 *
 * Events dispatched on window:
 *   'stt:interim'  → { text, identity, name }   (live, not final)
 *   'stt:final'    → { text, identity, name }    (committed sentence)
 *   'stt:started'  → {}
 *   'stt:stopped'  → {}
 *   'stt:error'    → { error }
 */

const STTEngine = (() => {
    // ── State ──────────────────────────────────────────────────────────────
    let recognition   = null;
    let isRunning     = false;
    let isMuted       = false;
    let restartTimer  = null;
    let identity      = 'local';
    let displayName   = 'User';
    let lang          = 'ar-SA';   // default Arabic; caller can override

    // ── Browser Support Check ──────────────────────────────────────────────
    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition || null;

    function isSupported() {
        return !!SpeechRecognition;
    }

    // ── Internal: fire custom event ────────────────────────────────────────
    function dispatch(name, detail = {}) {
        window.dispatchEvent(new CustomEvent(name, { detail }));
    }

    // ── Internal: build & wire recognition instance ────────────────────────
    function createRecognition() {
        if (!SpeechRecognition) return null;

        const rec       = new SpeechRecognition();
        rec.lang        = lang;
        rec.continuous  = true;
        rec.interimResults = true;
        rec.maxAlternatives = 1;

        rec.onstart = () => {
            isRunning = true;
            dispatch('stt:started');
        };

        rec.onresult = (event) => {
            if (isMuted) return;

            let interim = '';
            let final   = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    final += transcript;
                } else {
                    interim += transcript;
                }
            }

            if (final) {
                dispatch('stt:final', { text: final.trim(), identity, name: displayName });
            } else if (interim) {
                dispatch('stt:interim', { text: interim.trim(), identity, name: displayName });
            }
        };

        rec.onerror = (event) => {
            // ignore non-critical errors
            if (['aborted', 'no-speech'].includes(event.error)) return;

            dispatch('stt:error', { error: event.error });

            if (event.error === 'not-allowed') {
                isRunning = false;
                dispatch('stt:stopped');
            }
        };

        rec.onend = () => {
            isRunning = false;
            // Auto-restart unless explicitly stopped or muted
            if (!isMuted && recognition) {
                restartTimer = setTimeout(() => {
                    try { recognition.start(); } catch (_) {}
                }, 800);
            } else {
                dispatch('stt:stopped');
            }
        };

        return rec;
    }

    // ── Public API ─────────────────────────────────────────────────────────

    /**
     * start({ identity, name, lang })
     * Begin speech recognition.
     */
    function start(opts = {}) {
        if (!isSupported()) {
            console.warn('[STT] Web Speech API not supported in this browser.');
            dispatch('stt:error', { error: 'not-supported' });
            return;
        }

        if (opts.identity)  identity    = opts.identity;
        if (opts.name)      displayName = opts.name;
        if (opts.lang)      lang        = opts.lang;

        isMuted = false;

        if (!recognition) {
            recognition = createRecognition();
        }

        try {
            recognition.start();
        } catch (e) {
            // already started — OK
        }
    }

    /**
     * stop()
     * Permanently stop (clears auto-restart).
     */
    function stop() {
        isMuted = true;
        clearTimeout(restartTimer);

        if (recognition) {
            try { recognition.stop(); } catch (_) {}
            recognition = null;
        }

        isRunning = false;
        dispatch('stt:stopped');
    }

    /**
     * setMuted(bool)
     * Pause/resume transcription without destroying the engine.
     * When muted the mic stays open but results are ignored.
     */
    function setMuted(muted) {
        isMuted = muted;

        if (muted) {
            clearTimeout(restartTimer);
            // Don't call recognition.stop() — avoids the restart loop being killed
            // Results will be silently discarded in onresult
        } else {
            // If we're not running, restart
            if (!isRunning && recognition) {
                try { recognition.start(); } catch (_) {}
            } else if (!isRunning) {
                recognition = createRecognition();
                try { recognition.start(); } catch (_) {}
            }
        }
    }

    /**
     * setLang(langCode)
     * Change language at runtime (e.g. 'en-US', 'ar-SA').
     * Restarts the engine so the new language takes effect.
     */
    function setLang(langCode) {
        lang = langCode;
        if (isRunning) {
            stop();
            setTimeout(() => start(), 500);
        }
    }

    function getState() {
        return { isRunning, isMuted, lang, identity, displayName };
    }

    // ── Expose ─────────────────────────────────────────────────────────────
    return { start, stop, setMuted, setLang, getState, isSupported };
})();

// Make globally available
window.STTEngine = STTEngine;

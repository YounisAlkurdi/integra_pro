/**
 * integra-session.js — UI Controller
 *
 * This file ONLY handles the DOM / UI layer.
 * All LiveKit logic is in livekit-session.js
 * All STT logic is in stt.js
 *
 * Listens to custom events from both modules and updates the UI.
 */

document.addEventListener('DOMContentLoaded', () => {

    // ── Init icons ───────────────────────────────────────────────────────────
    if (window.lucide) window.lucide.createIcons();

    // ── State ────────────────────────────────────────────────────────────────
    let micEnabled    = true;
    let camEnabled    = true;
    let screenSharing = false;
    let sttEnabled    = false;
    let sessionSeconds = 0;
    let timerInterval  = null;
    let localRole      = 'hr';

    // ── DOM refs ─────────────────────────────────────────────────────────────
    const $ = id => document.getElementById(id);
    const localVideo       = $('local-video');
    const remoteVideo      = $('remote-video');
    const remotePlaceholder= $('remote-placeholder');
    const joinLobby        = $('join-lobby');
    const adminFeed        = $('admin-feed');
    const candidateFeed    = $('candidate-feed');
    const adminStatus      = $('admin-status');
    const candidateStatus  = $('candidate-status');
    const connectionBadge  = $('connection-badge');
    const sttActiveDot     = $('stt-active-dot');
    const timerEl          = $('timer');
    const logList          = $('log-list');
    const camOffPlaceholder = $('camera-off-placeholder');

    // ── Timer ────────────────────────────────────────────────────────────────
    function startTimer() {
        timerInterval = setInterval(() => {
            sessionSeconds++;
            const m = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
            const s = String(sessionSeconds % 60).padStart(2, '0');
            if (timerEl) timerEl.textContent = `${m}:${s}`;
        }, 1000);
    }

    // ── Toast Notification ───────────────────────────────────────────────────
    window.showToast = function(message, type = 'info') {
        const colors = {
            success: 'border-green-500/30 text-green-400',
            error:   'border-red-500/30   text-red-400',
            info:    'border-cyan-400/30  text-cyan-400',
        };
        const container = $('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `glass-panel px-6 py-3 rounded-2xl border ${colors[type] || colors.info} text-[10px] font-mono uppercase tracking-widest animate-slide-up`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3500);
    };

    // ── Add Intel Log Entry ──────────────────────────────────────────────────
    function addLog(message, type = 'system') {
        if (!logList) return;
        const colors = { system: 'text-white/40', audio: 'text-cyan-400', video: 'text-purple-400', error: 'text-red-400' };
        const empty = logList.querySelector('[data-empty]');
        if (empty) empty.remove();

        const el = document.createElement('div');
        el.className = `${colors[type] || colors.system} flex items-start gap-2`;
        el.innerHTML = `<span class="text-white/20 shrink-0">${new Date().toLocaleTimeString('en', { hour12: false })}</span>${message}`;
        logList.appendChild(el);
        logList.scrollTop = logList.scrollHeight;
    }

    // ── Append Transcription to a Feed ──────────────────────────────────────
    function appendTranscription(feedEl, text, isFinal, statusEl) {
        if (!feedEl) return;

        // Update status badge
        if (statusEl) {
            statusEl.textContent = 'LIVE';
            statusEl.className = 'text-[9px] font-mono text-cyan-400 uppercase tracking-[0.3em] animate-pulse';
        }

        // Find or create interim bubble
        let bubble = feedEl.querySelector('[data-interim]');

        if (!isFinal) {
            if (!bubble) {
                bubble = document.createElement('div');
                bubble.setAttribute('data-interim', '1');
                bubble.className = 'text-xs text-white/40 font-mono leading-relaxed italic border-l-2 border-white/10 pl-3';
                feedEl.appendChild(bubble);
            }
            bubble.textContent = text;
        } else {
            // Remove interim bubble
            if (bubble) bubble.remove();

            const el = document.createElement('div');
            el.className = 'text-xs text-white/80 font-medium leading-relaxed border-l-2 border-cyan-400/40 pl-3 animate-slide-up';
            el.innerHTML = `<span class="text-white/20 text-[9px] font-mono mr-2">${new Date().toLocaleTimeString('en', { hour12: false })}</span>${text}`;
            feedEl.appendChild(el);
            feedEl.scrollTop = feedEl.scrollHeight;
        }
    }

    // ────────────────────────────────────────────────────────────────────────
    // LiveKit events → UI
    // ────────────────────────────────────────────────────────────────────────

    window.addEventListener('lk:connected', (e) => {
        const { participantName, role, roomName } = e.detail;
        localRole = role;

        // Hide lobby, show session
        if (joinLobby) joinLobby.style.display = 'none';

        // Update connection badge
        if (connectionBadge) {
            connectionBadge.textContent = 'LIVE';
            connectionBadge.className = 'text-[9px] font-mono px-3 py-1 rounded-full bg-cyan-400/10 border border-cyan-400/30 text-cyan-400 uppercase tracking-widest animate-pulse';
        }

        // Update local label
        const localLabel = $('local-label');
        if (localLabel) localLabel.textContent = participantName;

        // Update admin status (local user is HR or candidate)
        if (role === 'hr' && adminStatus) {
            adminStatus.textContent = 'LIVE';
            adminStatus.className = 'text-[9px] font-mono text-cyan-400 uppercase tracking-[0.3em] animate-pulse';
        } else if (role === 'candidate' && candidateStatus) {
            candidateStatus.textContent = 'LIVE';
            candidateStatus.className = 'text-[9px] font-mono text-cyan-400 uppercase tracking-[0.3em] animate-pulse';
        }

        addLog(`Connected to room: ${roomName} as ${role.toUpperCase()}`);
        startTimer();
        showToast(`Connected as ${participantName}`, 'success');

        // Start STT
        if (window.STTEngine?.isSupported()) {
            window.STTEngine.start({
                identity: participantName,
                name: participantName,
                lang: window.APP_CONFIG?.sttLang || 'ar-SA',
            });
            sttEnabled = true;
            if (sttActiveDot) sttActiveDot.classList.remove('hidden');
        }

        // Attach local video stream from camera
        try {
            const room = window.LiveKitSession.getRoom();
            if (room?.localParticipant) {
                // Find camera track
                room.localParticipant.trackPublications.forEach((pub) => {
                    if (pub.track && pub.source === 'camera') {
                        const stream = new MediaStream([pub.track.mediaStreamTrack]);
                        if (localVideo) {
                            localVideo.srcObject = stream;
                            if (camOffPlaceholder) camOffPlaceholder.classList.add('hidden');
                        }
                    }
                });
            }
        } catch (e) {
            console.warn('[UI] Could not attach local video:', e);
        }
    });

    window.addEventListener('lk:disconnected', () => {
        clearInterval(timerInterval);

        if (connectionBadge) {
            connectionBadge.textContent = 'OFFLINE';
            connectionBadge.className = 'text-[9px] font-mono px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/30 uppercase tracking-widest';
        }

        addLog('Session disconnected', 'error');
        showToast('Session ended', 'error');
    });

    window.addEventListener('lk:participant-joined', (e) => {
        const { name, role } = e.detail;
        addLog(`${name} joined as ${role.toUpperCase()}`, 'audio');
        showToast(`${name} joined the session`, 'success');

        if (role === 'candidate' && candidateStatus) {
            candidateStatus.textContent = 'LIVE';
            candidateStatus.className = 'text-[9px] font-mono text-cyan-400 uppercase tracking-[0.3em] animate-pulse';
        }
    });

    window.addEventListener('lk:participant-left', (e) => {
        const { name } = e.detail;
        addLog(`${name} left the session`, 'system');
        showToast(`${name} disconnected`, 'error');

        // Hide remote video
        if (remoteVideo) remoteVideo.classList.add('hidden');
        if (remotePlaceholder) remotePlaceholder.classList.remove('hidden');
    });

    window.addEventListener('lk:track-subscribed', (e) => {
        const { identity, kind, track, element } = e.detail;
        addLog(`Track subscribed: ${kind} from ${identity}`, 'video');

        if (kind === 'video' && remoteVideo) {
            // Attach to our statically defined remote-video element
            const stream = new MediaStream([track.mediaStreamTrack]);
            remoteVideo.srcObject = stream;
            remoteVideo.classList.remove('hidden');
            if (remotePlaceholder) remotePlaceholder.classList.add('hidden');
        }

        if (kind === 'audio' && element) {
            // Append hidden audio element to body so it plays
            element.style.display = 'none';
            document.body.appendChild(element);
        }
    });

    window.addEventListener('lk:track-unsubscribed', (e) => {
        if (e.detail.kind === 'video') {
            if (remoteVideo) remoteVideo.classList.add('hidden');
            if (remotePlaceholder) remotePlaceholder.classList.remove('hidden');
        }
    });

    window.addEventListener('lk:speaking-changed', (e) => {
        const { speakers } = e.detail;
        // Could add visual speaking indicator here
        speakers.forEach(id => {
            const el = document.querySelector(`[data-identity="${id}"]`);
            if (el) el.classList.add('speaking');
        });
    });

    window.addEventListener('lk:error', (e) => {
        const { message } = e.detail;
        addLog(`Error: ${message}`, 'error');
        showToast(message, 'error');

        // Re-enable join button
        const joinBtn = $('btn-join');
        if (joinBtn) {
            joinBtn.disabled = false;
            joinBtn.textContent = 'Connect to Session';
        }
    });

    // ────────────────────────────────────────────────────────────────────────
    // Transcriptions → feed UI
    // ────────────────────────────────────────────────────────────────────────

    // Local STT (my own speech)
    window.addEventListener('stt:final', (e) => {
        const { text } = e.detail;
        const { localRole: role } = window.LiveKitSession?.getState?.() || {};
        const myRole = role || localRole;
        const feed = myRole === 'candidate' ? candidateFeed : adminFeed;
        const status = myRole === 'candidate' ? candidateStatus : adminStatus;
        appendTranscription(feed, text, true, status);
    });

    window.addEventListener('stt:interim', (e) => {
        const { text } = e.detail;
        const { localRole: role } = window.LiveKitSession?.getState?.() || {};
        const myRole = role || localRole;
        const feed = myRole === 'candidate' ? candidateFeed : adminFeed;
        appendTranscription(feed, text, false, null);
    });

    // Remote participant transcriptions (via LiveKit data channel)
    window.addEventListener('lk:transcription', (e) => {
        const { identity, name, text, isFinal } = e.detail;
        const room = window.LiveKitSession?.getRoom();
        const localId = room?.localParticipant?.identity;

        // Determine if sender is candidate or HR (from their metadata)
        let remoteRole = 'unknown';
        if (room) {
            const p = room.remoteParticipants.get(identity);
            if (p?.metadata) {
                try { remoteRole = JSON.parse(p.metadata).role || 'unknown'; } catch (_) {}
            }
        }

        const feed = remoteRole === 'candidate' ? candidateFeed : adminFeed;
        const status = remoteRole === 'candidate' ? candidateStatus : adminStatus;
        appendTranscription(feed, text, isFinal, status);
    });

    // ────────────────────────────────────────────────────────────────────────
    // Control Bar
    // ────────────────────────────────────────────────────────────────────────

    $('btn-toggle-mic')?.addEventListener('click', async () => {
        const newState = await window.LiveKitSession?.toggleMic();
        micEnabled = newState ?? !micEnabled;
        updateControlBtn('btn-toggle-mic', micEnabled, 'mic', 'mic-off');
        window.STTEngine?.setMuted(!micEnabled);
        addLog(micEnabled ? 'Microphone enabled' : 'Microphone muted');
    });

    $('btn-toggle-cam')?.addEventListener('click', async () => {
        const newState = await window.LiveKitSession?.toggleCamera();
        camEnabled = newState ?? !camEnabled;
        updateControlBtn('btn-toggle-cam', camEnabled, 'video', 'video-off');
        if (camOffPlaceholder) camOffPlaceholder.classList.toggle('hidden', camEnabled);
    });

    $('btn-screenshare')?.addEventListener('click', async () => {
        const newState = await window.LiveKitSession?.toggleScreenShare();
        screenSharing = newState ?? !screenSharing;
        updateControlBtn('btn-screenshare', !screenSharing, 'monitor', 'monitor-x');
        showToast(screenSharing ? 'Screen share started' : 'Screen share stopped', 'info');
    });

    $('btn-toggle-stt')?.addEventListener('click', () => {
        if (!window.STTEngine?.isSupported()) {
            showToast('Speech recognition not supported in this browser', 'error');
            return;
        }
        sttEnabled = !sttEnabled;
        if (sttEnabled) {
            const state = window.LiveKitSession?.getState();
            window.STTEngine.start({
                identity: state?.localIdentity || 'local',
                name: state?.localName || 'User',
                lang: window.APP_CONFIG?.sttLang || 'ar-SA',
            });
            if (sttActiveDot) sttActiveDot.classList.remove('hidden');
            showToast('Transcription engine active', 'success');
        } else {
            window.STTEngine.stop();
            if (sttActiveDot) sttActiveDot.classList.add('hidden');
            showToast('Transcription paused', 'info');
        }
    });

    // ── Helper: update icon + active state of a control button ───────────────
    function updateControlBtn(id, isActive, iconOn, iconOff) {
        const btn = $(id);
        if (!btn) return;
        const icon = btn.querySelector('i[data-lucide]');
        if (icon) {
            icon.setAttribute('data-lucide', isActive ? iconOn : iconOff);
            window.lucide?.createIcons({ nodes: [icon] });
        }
        btn.classList.toggle('border-cyan-400/40', isActive);
        btn.classList.toggle('text-cyan-400', isActive);
    }

    // ── Tab switching ────────────────────────────────────────────────────────
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.remove('active');
                b.classList.add('text-white/30');
            });
            btn.classList.add('active');
            btn.classList.remove('text-white/30');

            document.querySelectorAll('[id$="-tab"]').forEach(el => el.classList.add('hidden'));
            const target = $(`${tab}-tab`);
            if (target) target.classList.remove('hidden');
        });
    });

    // ── Audio Visualizer Bars ────────────────────────────────────────────────
    const audioBars = $('audio-bars');
    if (audioBars) {
        for (let i = 0; i < 48; i++) {
            const bar = document.createElement('div');
            bar.className = 'flex-1 rounded-full bg-cyan-400/40 transition-all duration-100';
            bar.style.height = '4px';
            audioBars.appendChild(bar);
        }

        function animateBars() {
            audioBars.querySelectorAll('div').forEach(bar => {
                const h = sttEnabled && micEnabled
                    ? Math.random() * 100 + 4
                    : Math.random() * 8 + 2;
                bar.style.height = `${h}%`;
                bar.style.opacity = sttEnabled && micEnabled ? '0.6' : '0.15';
            });
            requestAnimationFrame(animateBars);
        }
        animateBars();
    }

    // ── Initial camera preview (before joining) ──────────────────────────────
    async function initPreviewCamera() {
        try {
            if (!navigator.mediaDevices) return;
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            if (localVideo) {
                localVideo.srcObject = stream;
            }
        } catch (e) {
            // Camera denied before join — OK
            console.warn('[Preview] Camera not available pre-join');
        }
    }
    initPreviewCamera();

    // ── Initial log ──────────────────────────────────────────────────────────
    if (logList) {
        logList.innerHTML = ''; // clear placeholder
        addLog('System initialized. Awaiting session...');
    }

});

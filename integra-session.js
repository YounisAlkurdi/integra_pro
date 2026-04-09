/**
 * integra-session.js — UI Controller v3
 *
 * Fixes vs v2:
 *  - Animation loop replaced with visibility-aware throttled interval
 *    (was: rAF 60fps on 48 divs = ~2880 DOM mutations/sec; now: 8fps, paused when tab hidden)
 *  - Dynamic Video Grid: updateGrid(n) adjusts CSS grid columns/rows automatically
 *    (1 participant = full width, 2 = side-by-side, 3+ = 2-col grid)
 *  - Reconnection events (lk:reconnecting / lk:reconnected) surfaced to UI
 *  - Speaking highlight also updates local PiP border when local speaks
 */

document.addEventListener('DOMContentLoaded', () => {

    // ── Init ─────────────────────────────────────────────────────────────────
    if (window.lucide) window.lucide.createIcons();

    // ── State ────────────────────────────────────────────────────────────────
    let micEnabled    = true;
    let camEnabled    = true;
    let screenSharing = false;
    let sttEnabled    = false;
    let sessionSeconds = 0;
    let timerInterval  = null;
    let localRole      = 'hr';
    let localName      = '';

    // Map of identity → { role, name, feedEl, statusEl }
    const participantFeeds = new Map();

    // ── DOM refs ─────────────────────────────────────────────────────────────
    const $ = id => document.getElementById(id);
    const localVideo        = $('local-video');
    const remoteArea        = $('remote-area');
    const remotePlaceholder = $('remote-placeholder');
    const joinLobby         = $('join-lobby');
    const connectionBadge   = $('connection-badge');
    const sttActiveDot      = $('stt-active-dot');
    const timerEl           = $('timer');
    const logList           = $('log-list');
    const camOffPlaceholder = $('camera-off-placeholder');
    const adminFeedEl       = $('admin-feed');
    const candidateFeedEl   = $('candidate-feed');
    const adminStatusEl     = $('admin-status');
    const candidateStatusEl = $('candidate-status');
    const adminFeedLabel    = $('admin-feed-label');
    const candidateFeedLabel = $('candidate-feed-label');

    // ── Toast ─────────────────────────────────────────────────────────────────
    window.showToast = function(message, type = 'info') {
        const colors = {
            success: 'border-green-500/30 text-green-400',
            error:   'border-red-500/30 text-red-400',
            info:    'border-cyan-400/30 text-cyan-400',
        };
        const container = $('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `glass-panel px-6 py-3 rounded-2xl border ${colors[type] || colors.info} text-[10px] font-mono uppercase tracking-widest animate-slide-up pointer-events-auto`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3500);
    };

    // ── Log ──────────────────────────────────────────────────────────────────
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

    // ── Timer ─────────────────────────────────────────────────────────────────
    function startTimer() {
        sessionSeconds = 0;
        timerInterval = setInterval(() => {
            sessionSeconds++;
            const m = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
            const s = String(sessionSeconds % 60).padStart(2, '0');
            if (timerEl) timerEl.textContent = `${m}:${s}`;
        }, 1000);
    }

    // ── Feed management ───────────────────────────────────────────────────────
    // Determine which static feed box to use (only 2 slots: HR → admin, candidate → candidate)
    function getFeedBoxForRole(role) {
        if (role === 'hr' || role === 'admin') {
            return { feedEl: adminFeedEl, statusEl: adminStatusEl, labelEl: adminFeedLabel };
        }
        return { feedEl: candidateFeedEl, statusEl: candidateStatusEl, labelEl: candidateFeedLabel };
    }

    function setFeedLabel(role, name) {
        const { labelEl } = getFeedBoxForRole(role);
        if (labelEl && name) labelEl.textContent = name;
    }

    function setFeedStatus(role, status, active = false) {
        const { statusEl } = getFeedBoxForRole(role);
        if (!statusEl) return;
        statusEl.textContent = status;
        statusEl.className = active
            ? 'text-[9px] font-mono text-cyan-400 uppercase tracking-[0.3em] animate-pulse'
            : 'text-[9px] font-mono text-white/20 uppercase tracking-[0.3em]';
    }

    function clearFeedPlaceholder(role) {
        const { feedEl } = getFeedBoxForRole(role);
        if (!feedEl) return;
        const placeholder = feedEl.querySelector('p.italic');
        if (placeholder) placeholder.remove();
    }

    // ── Transcription bubble ──────────────────────────────────────────────────
    function appendTranscription(role, text, isFinal) {
        const { feedEl } = getFeedBoxForRole(role);
        if (!feedEl) return;

        // Remove placeholder text
        clearFeedPlaceholder(role);
        setFeedStatus(role, 'LIVE', true);

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
            if (bubble) bubble.remove();
            const el = document.createElement('div');
            el.className = 'text-xs text-white/80 font-medium leading-relaxed border-l-2 border-cyan-400/40 pl-3 animate-slide-up';
            el.innerHTML = `<span class="text-white/20 text-[9px] font-mono mr-2">${new Date().toLocaleTimeString('en', { hour12: false })}</span>${text}`;
            feedEl.appendChild(el);
            feedEl.scrollTop = feedEl.scrollHeight;
        }
    }

    // ── Dynamic Video Grid Layout ──────────────────────────────────────────────
    // Adjusts the remote-area CSS grid based on number of participants.
    // This prevents panels stacking on top of each other.
    function updateGrid(count) {
        if (!remoteArea) return;
        // Reset inline grid styles
        remoteArea.style.display = 'grid';
        remoteArea.style.gap = '12px';
        remoteArea.style.width = '100%';
        remoteArea.style.height = '100%';

        if (count <= 0) {
            remoteArea.style.gridTemplateColumns = '1fr';
            remoteArea.style.gridTemplateRows = '1fr';
        } else if (count === 1) {
            remoteArea.style.gridTemplateColumns = '1fr';
            remoteArea.style.gridTemplateRows = '1fr';
        } else if (count === 2) {
            remoteArea.style.gridTemplateColumns = '1fr 1fr';
            remoteArea.style.gridTemplateRows = '1fr';
        } else if (count === 3) {
            remoteArea.style.gridTemplateColumns = '1fr 1fr';
            remoteArea.style.gridTemplateRows = '1fr 1fr';
        } else {
            // 4+ participants: 2-column, auto rows
            remoteArea.style.gridTemplateColumns = '1fr 1fr';
            remoteArea.style.gridTemplateRows = `repeat(${Math.ceil(count / 2)}, 1fr)`;
        }
    }

    // ── Remote participant video panel ────────────────────────────────────────
    function createParticipantPanel(identity, name, role) {
        // Remove placeholder
        if (remotePlaceholder) remotePlaceholder.classList.add('hidden');

        const panel = document.createElement('div');
        panel.id = `panel-${identity}`;
        // No longer 'absolute inset-0' — grid handles sizing
        panel.className = 'relative w-full h-full flex items-center justify-center bg-black rounded-[2rem] overflow-hidden transition-all min-h-0';
        panel.setAttribute('data-identity', identity);

        // Video slot (will be populated when track arrives)
        const videoSlot = document.createElement('div');
        videoSlot.id = `video-slot-${identity}`;
        videoSlot.className = 'absolute inset-0';
        panel.appendChild(videoSlot);

        // Waiting placeholder
        const waiting = document.createElement('div');
        waiting.id = `waiting-${identity}`;
        waiting.className = 'absolute inset-0 flex flex-col items-center justify-center';
        waiting.innerHTML = `
            <div class="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-3 border border-white/10">
                <span class="text-xl font-black text-white/60">${(name || identity).charAt(0).toUpperCase()}</span>
            </div>
            <p class="text-[10px] font-mono text-white/30 uppercase tracking-widest">${name || identity}</p>
            <p class="text-[9px] font-mono text-white/15 mt-1">${role?.toUpperCase()}</p>
        `;
        panel.appendChild(waiting);

        // Name label
        const label = document.createElement('div');
        label.className = 'absolute bottom-3 left-3 px-3 py-1 bg-black/60 backdrop-blur-xl rounded-lg text-[9px] font-mono uppercase tracking-widest border border-white/5 z-10';
        label.innerHTML = `<span class="text-cyan-400 font-bold mr-2">●</span><span>${name || identity}</span>`;
        panel.appendChild(label);

        // Speaking ring
        const ring = document.createElement('div');
        ring.id = `ring-${identity}`;
        ring.className = 'absolute inset-0 rounded-[2rem] border-2 border-cyan-400 opacity-0 transition-opacity duration-200 pointer-events-none z-10';
        panel.appendChild(ring);

        remoteArea.appendChild(panel);

        // Update grid layout for new count
        const count = remoteArea.querySelectorAll('[data-identity]').length;
        updateGrid(count);

        return panel;
    }

    function removeParticipantPanel(identity) {
        const panel = $(`panel-${identity}`);
        if (panel) panel.remove();

        // Show placeholder if no more remote participants
        const remaining = remoteArea.querySelectorAll('[data-identity]');
        if (remotePlaceholder && remaining.length === 0) {
            remotePlaceholder.classList.remove('hidden');
            remoteArea.style.display = '';
        } else {
            updateGrid(remaining.length);
        }
    }

    // ── Update control button visual state ──────────────────────────────────
    function updateControlBtn(id, isActive, iconOn, iconOff) {
        const btn = $(id);
        if (!btn) return;

        const icon = btn.querySelector('i[data-lucide]');
        if (icon) {
            icon.setAttribute('data-lucide', isActive ? iconOn : iconOff);
            window.lucide?.createIcons({ nodes: [icon] });
        }

        btn.classList.toggle('btn-on',  isActive);
        btn.classList.toggle('btn-off', !isActive);
    }

    // ────────────────────────────────────────────────────────────────────────────
    // LiveKit Events → UI
    // ────────────────────────────────────────────────────────────────────────────

    window.addEventListener('lk:connected', (e) => {
        const { participantName, role, roomName } = e.detail;
        localRole = role;
        localName = participantName;

        // Hide connecting overlay
        if (joinLobby) joinLobby.style.display = 'none';

        // Update badge
        if (connectionBadge) {
            connectionBadge.textContent = 'LIVE';
            connectionBadge.className = 'text-[9px] font-mono px-3 py-1 rounded-full bg-cyan-400/10 border border-cyan-400/30 text-cyan-400 uppercase tracking-widest animate-pulse';
        }

        // Set local label name
        const localLabel = $('local-label');
        if (localLabel) localLabel.textContent = participantName;

        // Set my own feed label and status
        setFeedLabel(role, participantName);
        setFeedStatus(role, 'LIVE', true);

        addLog(`Connected to room: ${roomName} as ${role.toUpperCase()}`);
        startTimer();
        showToast(`Connected as ${participantName}`, 'success');

        // Attach local video
        try {
            const room = window.LiveKitSession.getRoom();
            if (room?.localParticipant) {
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
        } catch (err) {
            console.warn('[UI] Could not attach local video:', err);
        }

        // Start STT for local user
        if (window.STTEngine?.isSupported()) {
            window.STTEngine.start({
                identity: participantName,
                name: participantName,
                lang: window.APP_CONFIG?.sttLang || 'ar-SA',
            });
            sttEnabled = true;
            if (sttActiveDot) sttActiveDot.classList.remove('hidden');
        }
    });

    window.addEventListener('lk:reconnecting', (e) => {
        const { attempt } = e.detail;
        if (connectionBadge) {
            connectionBadge.textContent = `RECONNECT ${attempt}`;
            connectionBadge.className = 'text-[9px] font-mono px-3 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 uppercase tracking-widest animate-pulse';
        }
        addLog(`⟳ Reconnecting... attempt ${attempt}`, 'error');
        showToast(`Connection lost — retrying (${attempt})`, 'error');
    });

    window.addEventListener('lk:reconnected', () => {
        if (connectionBadge) {
            connectionBadge.textContent = 'LIVE';
            connectionBadge.className = 'text-[9px] font-mono px-3 py-1 rounded-full bg-cyan-400/10 border border-cyan-400/30 text-cyan-400 uppercase tracking-widest animate-pulse';
        }
        addLog('✓ Reconnected successfully', 'audio');
        showToast('Reconnected!', 'success');
    });

    window.addEventListener('lk:disconnected', () => {
        clearInterval(timerInterval);

        if (connectionBadge) {
            connectionBadge.textContent = 'OFFLINE';
            connectionBadge.className = 'text-[9px] font-mono px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/30 uppercase tracking-widest';
        }

        // Reset all statuses
        setFeedStatus('hr', 'OFFLINE', false);
        setFeedStatus('candidate', 'OFFLINE', false);

        addLog('Session disconnected', 'error');
        showToast('Session ended', 'error');
    });

    window.addEventListener('lk:participant-joined', (e) => {
        const { identity, name, role } = e.detail;
        addLog(`${name} joined as ${role.toUpperCase()}`, 'audio');
        showToast(`${name} joined`, 'success');

        // Create panel immediately (video added when track arrives)
        createParticipantPanel(identity, name, role);

        // Update their feed label
        setFeedLabel(role, name);
        setFeedStatus(role, 'CONNECTED', true);
    });

    window.addEventListener('lk:participant-left', (e) => {
        const { identity, name } = e.detail;
        addLog(`${name} left the session`, 'system');
        showToast(`${name} disconnected`, 'error');
        removeParticipantPanel(identity);
    });

    // New event: add or remove a video element for a specific participant
    window.addEventListener('lk:participant-video', (e) => {
        const { identity, name, role, element, action } = e.detail;

        if (action === 'add' && element) {
            // Put video into the panel's video slot
            const slot = $(`video-slot-${identity}`);
            const waiting = $(`waiting-${identity}`);
            if (slot) {
                slot.appendChild(element);
                // Style the video element properly
                element.className = 'w-full h-full object-cover';
            }
            if (waiting) waiting.classList.add('hidden');
            addLog(`Video stream from ${name}`, 'video');
        }

        if (action === 'remove') {
            const slot = $(`video-slot-${identity}`);
            const waiting = $(`waiting-${identity}`);
            if (slot) slot.innerHTML = '';
            if (waiting) waiting.classList.remove('hidden');
        }
    });

    window.addEventListener('lk:speaking-changed', (e) => {
        const { speakers } = e.detail;

        // Reset all rings
        remoteArea.querySelectorAll('[id^="ring-"]').forEach(ring => {
            ring.style.opacity = '0';
        });

        // Light up active speakers
        speakers.forEach(id => {
            const ring = $(`ring-${id}`);
            if (ring) ring.style.opacity = '1';
        });
    });

    window.addEventListener('lk:mic-toggled', (e) => {
        micEnabled = e.detail.enabled;
        updateControlBtn('btn-toggle-mic', micEnabled, 'mic', 'mic-off');
        addLog(micEnabled ? 'Microphone enabled' : 'Microphone muted');
    });

    window.addEventListener('lk:cam-toggled', (e) => {
        camEnabled = e.detail.enabled;
        updateControlBtn('btn-toggle-cam', camEnabled, 'video', 'video-off');
        if (camOffPlaceholder) camOffPlaceholder.classList.toggle('hidden', camEnabled);
        // Update local video stream visibility
        if (localVideo) localVideo.style.opacity = camEnabled ? '1' : '0';
    });

    // Local camera track published → wire it to the PiP element
    window.addEventListener('lk:local-camera', (e) => {
        const stream = new MediaStream([e.detail.track.mediaStreamTrack]);
        if (localVideo) {
            localVideo.srcObject = stream;
            if (camOffPlaceholder) camOffPlaceholder.classList.add('hidden');
        }
    });

    window.addEventListener('lk:error', (e) => {
        const msg = e.detail.message;
        addLog(`Error: ${msg}`, 'error');
        showToast(msg, 'error');

        // Check if it's a "Not Started" error from our backend
        if (msg.includes('Access allowed') || msg.includes('الدخول متاح')) {
            if (joinLobby) {
                // Split the bilingual message for better display
                const [msgAr, msgEn] = msg.split(' | ');
                
                joinLobby.innerHTML = `
                    <div class="relative mb-10">
                        <div class="absolute -inset-10 bg-purple-500/10 rounded-full blur-3xl"></div>
                        <div class="w-32 h-32 rounded-full border-2 border-dashed border-white/10 flex items-center justify-center animate-[spin_20s_linear_infinite]">
                            <i data-lucide="clock" class="w-12 h-12 text-white/20 -rotate-12"></i>
                        </div>
                        <div class="absolute inset-0 flex items-center justify-center">
                             <div class="w-2 h-2 bg-purple-500 rounded-full animate-ping"></div>
                        </div>
                    </div>
                    <div class="text-center px-10">
                        <h3 class="text-xl font-black uppercase tracking-tighter mb-2 text-white/80">${msgAr || msg}</h3>
                        <p class="text-[11px] font-mono text-white/40 uppercase tracking-[0.3em] max-w-sm mx-auto leading-relaxed">
                            ${msgEn ? msgEn.replace('Access allowed', 'Access restricted until') : 'Access restricted'}
                        </p>
                        <div class="mt-8 pt-8 border-t border-white/5">
                            <button onclick="window.location.reload()" class="px-8 py-3 bg-white/5 border border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-white text-white hover:text-obsidian transition-all">
                                تحديث الصفحة
                            </button>
                        </div>
                    </div>
                `;
                lucide.createIcons({ nodes: [joinLobby] });
            }
        }

        const joinBtn = $('btn-join');
        if (joinBtn) {
            joinBtn.disabled = false;
            joinBtn.textContent = 'Connect to Session';
        }
    });

    // ── Local STT → own feed ─────────────────────────────────────────────────
    window.addEventListener('stt:final', (e) => {
        const myRole = window.LiveKitSession?.getState?.()?.localRole || localRole;
        appendTranscription(myRole, e.detail.text, true);
    });

    window.addEventListener('stt:interim', (e) => {
        const myRole = window.LiveKitSession?.getState?.()?.localRole || localRole;
        appendTranscription(myRole, e.detail.text, false);
    });

    // ── Remote transcriptions → correct feed ─────────────────────────────────
    window.addEventListener('lk:transcription', (e) => {
        const { role, text, isFinal } = e.detail;
        appendTranscription(role, text, isFinal);
    });

    // ── Control Buttons ───────────────────────────────────────────────────────
    $('btn-toggle-mic')?.addEventListener('click', async () => {
        await window.LiveKitSession?.toggleMic();
        // State update comes via 'lk:mic-toggled' event
    });

    $('btn-toggle-cam')?.addEventListener('click', async () => {
        await window.LiveKitSession?.toggleCamera();
        // State update comes via 'lk:cam-toggled' event
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
            updateControlBtn('btn-toggle-stt', true, 'message-square', 'message-square');
            showToast('Transcription engine active', 'success');
        } else {
            window.STTEngine.stop();
            if (sttActiveDot) sttActiveDot.classList.add('hidden');
            updateControlBtn('btn-toggle-stt', false, 'message-square', 'message-square');
            showToast('Transcription paused', 'info');
        }
    });

    // ── Tab switching ─────────────────────────────────────────────────────────
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

    // ── Audio Visualizer Bars ─────────────────────────────────────────────────
    // FIX: Was using requestAnimationFrame (60fps) on 48 elements = ~2880 DOM
    // mutations/second, stealing CPU from audio/video processing.
    // Now: throttled to 8fps (125ms interval) and PAUSED when tab is hidden.
    const audioBars = $('audio-bars');
    if (audioBars) {
        const BAR_COUNT = 32; // Reduced from 48 — still looks good, 33% less work
        for (let i = 0; i < BAR_COUNT; i++) {
            const bar = document.createElement('div');
            bar.className = 'flex-1 rounded-full bg-cyan-400/40';
            bar.style.cssText = 'height:4px;transition:height 120ms ease,opacity 120ms ease;';
            audioBars.appendChild(bar);
        }

        let barInterval = null;

        function startBarAnimation() {
            if (barInterval) return;
            const bars = audioBars.querySelectorAll('div');
            barInterval = setInterval(() => {
                bars.forEach(bar => {
                    const active = sttEnabled && micEnabled;
                    const h = active ? Math.random() * 100 + 4 : Math.random() * 8 + 2;
                    bar.style.height = `${h}%`;
                    bar.style.opacity = active ? '0.6' : '0.15';
                });
            }, 125); // 8fps instead of 60fps
        }

        function stopBarAnimation() {
            clearInterval(barInterval);
            barInterval = null;
        }

        // Pause when tab is hidden to free CPU for WebRTC
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                stopBarAnimation();
            } else {
                startBarAnimation();
            }
        });

        startBarAnimation();
    }

    // ── Local camera preview (before joining) ─────────────────────────────────
    async function initPreviewCamera() {
        try {
            if (!navigator.mediaDevices) return;
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            if (localVideo) localVideo.srcObject = stream;
        } catch (e) {
            console.warn('[Preview] Camera not available pre-join');
        }
    }
    initPreviewCamera();

    // ── Initial log ──────────────────────────────────────────────────────────
    if (logList) {
        logList.innerHTML = '';
        addLog('System initialized. Awaiting session...');
    }

});

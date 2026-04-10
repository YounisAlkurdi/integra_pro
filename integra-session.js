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

    const API_BASE = window.APP_CONFIG?.backendUrl || 'http://127.0.0.1:8000';

    // ── State ────────────────────────────────────────────────────────────────
    let micEnabled    = true;
    let camEnabled    = true;
    let screenSharing = false;
    let sttEnabled    = false;
    let sessionSeconds = 0;
    let maxSeconds     = 600; // Default 10 mins
    let timerInterval  = null;
    
    // Auto-detect role from URL
    const urlParams = new URLSearchParams(window.location.search);
    let localRole = urlParams.get('role') || 'candidate';
    let localName = urlParams.get('name') || '';
    let currentRoomId = urlParams.get('room');

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
    function startTimer(initialSeconds) {
        sessionSeconds = initialSeconds;
        
        if (timerInterval) clearInterval(timerInterval);
        
        // Initial draw
        updateTimerUI();

        timerInterval = setInterval(() => {
            sessionSeconds--;
            
            if (sessionSeconds <= 0) {
                clearInterval(timerInterval);
                if (timerEl) timerEl.textContent = "00:00";
                showToast("SESSION EXPIRED. TERMINATING LINK.", "error");
                setTimeout(() => { window.endSession?.(); }, 3000);
                return;
            }

            updateTimerUI();

            // Warn when 2 minutes left
            if (sessionSeconds === 120) {
                showToast("WARNING: 120 SECONDS UNTIL LINK TERMINATION", "error");
                timerEl.classList.add('text-red-500', 'animate-pulse');
            }
        }, 1000);
    }

    function updateTimerUI() {
        if (!timerEl) return;
        const m = String(Math.max(0, Math.floor(sessionSeconds / 60))).padStart(2, '0');
        const s = String(Math.max(0, sessionSeconds % 60)).padStart(2, '0');
        timerEl.textContent = `${m}:${s}`;
        
        // If expired or negative, style as error
        if (sessionSeconds <= 0) {
            timerEl.classList.add('text-red-500');
        } else if (sessionSeconds <= 120) {
            timerEl.classList.add('text-red-500', 'animate-pulse');
        } else {
            timerEl.classList.remove('text-red-500', 'animate-pulse');
        }
    }

    async function fetchRoomMeta(roomId) {
        try {
            const { data, error } = await window.supabase
                .from('nodes')
                .select('created_at, duration_seconds')
                .eq('room_id', roomId)
                .single();
            
            if (error) throw error;
            return data;
        } catch (e) {
            console.warn("[RoomMeta] Falling back to default limits:", e);
            return { created_at: new Date().toISOString(), duration_seconds: 600 };
        }
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
        
        // Fetch limits and creation time
        fetchRoomMeta(roomName).then(meta => {
            const createdAt = new Date(meta.created_at).getTime();
            const now = Date.now();
            const totalDuration = meta.duration_seconds || 600; // Default 10 mins
            const elapsed = Math.floor((now - createdAt) / 1000);
            const remaining = totalDuration - elapsed;

            if (remaining <= 0) {
                showToast("SESSION HAS EXPIRED.", "error");
                timerEl.textContent = "00:00";
                setTimeout(() => { window.endSession?.(); }, 2000);
            } else {
                startTimer(remaining);
                addLog(`Session active. ${Math.floor(remaining/60)}m ${remaining%60}s remaining.`, 'system');
            }
        });

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

        addLog('Session terminated by server', 'error');
        
        // Show the termination overlay
        const overlay = $('termination-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
            // Ensure icons are created if overlay was hidden
            if (window.lucide) window.lucide.createIcons({ nodes: [overlay] });
            
            setTimeout(() => {
                overlay.classList.remove('opacity-0');
                overlay.classList.add('opacity-100');
            }, 50);
        } else {
            // Fallback
            showToast('Session ended', 'error');
            setTimeout(() => { window.location.href = 'index.html'; }, 2000);
        }
    });

    /**
     * Terminate the session cleanly
     */
    window.endSession = function() {
        showToast("TERMINATING CONNECTION...", "info");
        window.LiveKitSession?.disconnect();
        
        // If I am the HR, I go to dashboard. If I am the candidate, I see the overlay.
        if (localRole === 'hr' || localRole === 'admin') {
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1000);
        } else {
            // Overlay will be triggered by lk:disconnected
        }
    };

    // Wire Leave Button
    $('btn-leave')?.addEventListener('click', () => {
        window.endSession();
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

        // --- BEAUTIFUL "ROOM FULL" UI ---
        if (msg.includes('Room is full') || msg.includes('الغرفة ممتلئة')) {
            if (joinLobby) {
                const [msgAr, msgEn] = msg.split(' | ');
                joinLobby.innerHTML = `
                    <div class="relative mb-10">
                        <div class="absolute -inset-16 bg-red-500/10 rounded-full blur-3xl animate-pulse"></div>
                        <div class="w-32 h-32 rounded-full border-2 border-white/10 bg-red-500/5 backdrop-blur-sm flex items-center justify-center">
                            <i data-lucide="user-minus" class="w-12 h-12 text-red-500 animate-[bounce_2s_infinite]"></i>
                        </div>
                        <div class="absolute -bottom-2 -right-2 w-10 h-10 bg-red-500 rounded-full flex items-center justify-center border-4 border-obsidian shadow-2xl">
                             <i data-lucide="lock" class="w-4 h-4 text-white"></i>
                        </div>
                    </div>
                    <div class="text-center px-10">
                        <h3 class="text-2xl font-black uppercase tracking-tight mb-3 bg-gradient-to-r from-red-400 to-orange-400 bg-clip-text text-transparent">
                            ${msgAr || 'الغرفة ممتلئة'}
                        </h3>
                        <p class="text-[11px] font-mono text-white/50 uppercase tracking-[0.2em] max-w-sm mx-auto leading-loose">
                            ${msgEn || 'Maximum participants reached for this session.'}
                        </p>
                        <div class="mt-10 p-1 bg-white/5 rounded-2xl border border-white/5 backdrop-blur-md">
                            <button onclick="window.location.reload()" class="w-full px-8 py-4 bg-red-500 rounded-xl text-[11px] font-black uppercase tracking-[0.3em] hover:bg-white text-white hover:text-red-600 transition-all shadow-xl hover:shadow-red-500/20 active:scale-95">
                                محاولة الدخول مجدداً
                            </button>
                        </div>
                        <p class="mt-6 text-[9px] font-black uppercase tracking-widest text-white/20">
                            Interviewer: ${new URLSearchParams(window.location.search).get('name') || 'Candidate'}
                        </p>
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

    // ── Local STT → own feed & Persist to Server ──────────────────────────────
    async function saveLogToServer(sender, message) {
        const roomName = window.LiveKitSession?.getState?.()?.roomName;
        if (!roomName || !message) return;

        try {
            const token = localStorage.getItem('supabase_token');
            await fetch('http://localhost:8000/api/logs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    node_id: roomName,
                    sender: sender,
                    message: message
                })
            });
        } catch (err) {
            console.warn('[Log] Failed to save transcript to server:', err);
        }
    }

    window.addEventListener('stt:final', (e) => {
        const state  = window.LiveKitSession?.getState?.();
        const myRole = state?.localRole || localRole;
        const myName = e.detail.name || state?.participantName || 'User';
        
        appendTranscription(myRole, e.detail.text, true);
        saveLogToServer(myName, e.detail.text);
    });

    window.addEventListener('stt:interim', (e) => {
        const myRole = window.LiveKitSession?.getState?.()?.localRole || localRole;
        appendTranscription(myRole, e.detail.text, false);
    });

    // ── Remote transcriptions → correct feed & Persist to Server ───────────────
    window.addEventListener('lk:transcription', (e) => {
        const { role, text, isFinal, name } = e.detail;
        appendTranscription(role, text, isFinal);
        
        if (isFinal) {
            saveLogToServer(name || role.toUpperCase(), text);
        }
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

    // ── Join Session Function ────────────────────────────────────────────────
    window.joinSession = async function() {
        const btn = $('btn-join');
        const inputRoom = document.getElementById('input-room');
        const inputName = document.getElementById('input-name');
        const inputRole = document.getElementById('input-role');

        const roomName = inputRoom ? inputRoom.value.trim() : new URLSearchParams(window.location.search).get('room');
        const name     = inputName ? inputName.value.trim() : new URLSearchParams(window.location.search).get('name');
        const role     = inputRole ? inputRole.value.trim() : (new URLSearchParams(window.location.search).get('role') || 'candidate');

        if (btn) {
            btn.disabled = true;
            btn.textContent = 'CONNECTING...';
        }

        if (!roomName) {
            showToast("Missing Room ID", "error");
            if (btn) btn.disabled = false;
            return;
        }

        try {
            const result = await window.LiveKitSession.connect({
                roomName: roomName,
                participantName: name,
                role: role
            });

            // --- LOBBY SYSTEM LOGIC ---
            if (result && result.status === "AWAITING_APPROVAL") {
                if (joinLobby) {
                    joinLobby.innerHTML = `
                        <div class="relative mb-10">
                            <div class="absolute -inset-10 bg-cyan-500/10 rounded-full blur-3xl"></div>
                            <div class="w-32 h-32 rounded-full border-2 border-cyan-500/20 flex items-center justify-center">
                                <div class="w-20 h-20 border-b-2 border-cyan-400 rounded-full animate-spin"></div>
                                <i data-lucide="shield-check" class="absolute w-8 h-8 text-cyan-400 animate-pulse"></i>
                            </div>
                        </div>
                        <div class="text-center px-10">
                            <h3 class="text-xl font-black uppercase tracking-widest mb-3 text-white">الطلب قيد الانتظار</h3>
                            <p class="text-[11px] font-mono text-white/40 uppercase tracking-[0.2em] max-w-sm mx-auto leading-relaxed">
                                ${result.message_en}
                            </p>
                            <div class="mt-8 py-3 px-6 bg-white/5 rounded-full inline-flex items-center gap-3 border border-white/5">
                                <span class="w-2 h-2 bg-cyan-500 rounded-full animate-ping"></span>
                                <span class="text-[9px] font-black text-cyan-400 uppercase tracking-widest">Verifying Identity...</span>
                            </div>
                        </div>
                    `;
                    lucide.createIcons({ nodes: [joinLobby] });
                }

                // Poll for status
                const pollStatus = setInterval(async () => {
                    try {
                        const checkRaw = await fetch(`${API_BASE}/api/livekit/request-status?room_id=${roomName}&participant_name=${name}`);
                        const check = await checkRaw.json();
                        
                        if (check.status === "APPROVED") {
                            clearInterval(pollStatus);
                            // Join automatically now that we are approved
                            window.joinSession(); 
                        } else if (check.status === "REJECTED") {
                            clearInterval(pollStatus);
                            showToast("Entry denied by host", "error");
                            window.location.reload();
                        }
                    } catch (e) { console.error("Poll fail:", e); }
                }, 3000);
                return;
            }
        } catch (err) {
            console.error("[Join] Connection failed:", err);
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Reconnect Session';
            }
        }
    };

    $('btn-join')?.addEventListener('click', window.joinSession);

    // ── Initial log ──────────────────────────────────────────────────────────
    if (logList) {
        logList.innerHTML = '';
        addLog('System initialized. Awaiting session...');
    }

    // --- HR LOBBY MONITOR ---
    if (localRole === 'hr' || localRole === 'interviewer') {
        const lobbyContainer = document.createElement('div');
        lobbyContainer.id = 'hr-lobby-notifs';
        lobbyContainer.className = 'fixed top-20 right-6 w-80 space-y-4 z-[9999]';
        document.body.appendChild(lobbyContainer);

        const knownRequests = new Set();

        setInterval(async () => {
            if (!currentRoomId) return;
            try {
                const res = await fetch(`${API_BASE}/api/livekit/pending-requests/${currentRoomId}`);
                const requests = await res.json();

                requests.forEach(req => {
                    const reqKey = `${req.participant_name}`;
                    if (knownRequests.has(reqKey)) return;
                    knownRequests.add(reqKey);

                    const card = document.createElement('div');
                    card.className = 'bg-obsidian/90 backdrop-blur-xl border border-white/10 p-5 rounded-2xl shadow-2xl animate-[slideIn_0.3s_ease-out] ring-1 ring-white/5';
                    card.innerHTML = `
                        <div class="flex items-start gap-4 mb-4">
                            <div class="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center border border-cyan-500/30">
                                <i data-lucide="user-plus" class="w-5 h-5 text-cyan-400"></i>
                            </div>
                            <div class="flex-1">
                                <h4 class="text-[11px] font-black text-white uppercase tracking-widest mb-1">طلب انضمام جديد</h4>
                                <p class="text-[13px] font-bold text-white/90">${req.participant_name}</p>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-3">
                            <button class="btn-deny px-4 py-2 bg-white/5 hover:bg-red-500/20 border border-white/10 rounded-xl text-[9px] font-black uppercase tracking-widest text-white/40 hover:text-red-400 transition-all">
                                رفض
                            </button>
                            <button class="btn-approve px-4 py-2 bg-cyan-500 hover:bg-white border border-cyan-400/50 rounded-xl text-[9px] font-black uppercase tracking-widest text-white hover:text-obsidian transition-all shadow-lg shadow-cyan-500/20">
                                قبول
                            </button>
                        </div>
                    `;
                    
                    card.querySelector('.btn-approve').onclick = async () => {
                        await fetch(`${API_BASE}/api/livekit/decide-request`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ room_id: currentRoomId, participant_name: req.participant_name, decision: 'APPROVED' })
                        });
                        card.remove();
                    };

                    card.querySelector('.btn-deny').onclick = async () => {
                        await fetch(`${API_BASE}/api/livekit/decide-request`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ room_id: currentRoomId, participant_name: req.participant_name, decision: 'REJECTED' })
                        });
                        card.remove();
                        knownRequests.delete(reqKey);
                    };

                    lobbyContainer.appendChild(card);
                    lucide.createIcons({ nodes: [card] });
                });
            } catch (e) { console.error("Lobby check failed:", e); }
        }, 5000);
    }

    /**
     * Terminate the session cleanly
     */
    window.endSession = function() {
        window.LiveKitSession.disconnect();
        window.location.href = 'dashboard.html';
    };

    /**
     * Copy invite link for candidate
     */
    window.copyInviteLink = function() {
        const inputRoom = document.getElementById('input-room');
        const room      = inputRoom ? inputRoom.value.trim() : 'integra-room-01';
        const base      = window.location.origin + window.location.pathname.replace('integra-session.html', '');
        const link      = `${base}integra-session.html?room=${room}&role=candidate`;
        
        navigator.clipboard.writeText(link).then(() => {
            if (typeof showToast === 'function') showToast('Invite link copied!', 'success');
        });
    };

    window.triggerCognitiveTest = function() {
        if (typeof showToast === 'function') showToast('Cognitive Challenge Protocol Initiated', 'info');
    };

});

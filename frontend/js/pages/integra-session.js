/**
 * integra-session.js — UI Controller v4 (Canvas Overlay Added)
 *
 * Changes vs v3:
 *  - candidateIdentity tracked alongside candidateVideo
 *  - createParticipantPanel() injects a <canvas> overlay per panel
 *  - drawForensicCanvas() draws bbox / zone label / head arrow / iris dots
 *    exactly like index.html — called at the end of updateForensicUI()
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
    let maxSeconds     = 600;
    let timerInterval  = null;

    const urlParams = new URLSearchParams(window.location.search);
    let localRole     = urlParams.get('role') || 'candidate';
    let localName     = urlParams.get('name') || '';
    let currentRoomId = urlParams.get('room');
    let aiAgentActive = urlParams.get('ai_agent') === 'true';

    const participantFeeds = new Map();
    let candidateVideo    = null;
    let candidateIdentity = null;   // ← NEW: track identity for canvas lookup
    let forensicWS        = null;
    let forensicInterval  = null;

    // ── FIX 1: $ defined FIRST before any usage ───────────────────────────────
    const $ = id => document.getElementById(id);

    // --- AI Agent Discovery: WebMCP Protocol (RFC-ready) ---
    if (window.navigator && window.navigator.modelContext) {
        window.navigator.modelContext.provideContext("integra-forensic-session", {
            roomId: currentRoomId,
            role: localRole,
            candidateName: localName,
            agentActive: aiAgentActive,
            capabilities: ["neural-command", "behavioral-analysis", "deepfake-shield"],
            status: "ready"
        });
        console.log("Integra: WebMCP Context Advertised");
    }


    // ── Spatial Grid Init ─────────────────────────────────────────────────────
    function initSpatialGrid() {
        const grid = $('spatialGrid');
        if (!grid) return;
        grid.innerHTML = '';
        for (let i = 0; i < 9; i++) {
            const cell = document.createElement('div');
            cell.className = "bg-white/5 border border-white/5 rounded-lg transition-all duration-300";
            grid.appendChild(cell);
        }
    }
    initSpatialGrid();

    // ── AI Agent UI Init ──────────────────────────────────────────────────────
    if (aiAgentActive) {
        const agentDashboard = $('ai-agent-dashboard');
        if (agentDashboard) agentDashboard.classList.remove('hidden');
        // Audio bars now stay visible in the bottom container regardless
    }

    // ── DOM refs ─────────────────────────────────────────────────────────────
    const localVideo         = $('local-video');
    const remoteArea         = $('remote-area');
    const remotePlaceholder  = $('remote-placeholder');
    const joinLobby          = $('join-lobby');
    const connectionBadge    = $('connection-badge');
    const sttActiveDot       = $('stt-active-dot');
    const timerEl            = $('timer');
    const logList            = $('log-list');
    const camOffPlaceholder  = $('camera-off-placeholder');
    const adminFeedEl        = $('admin-feed');
    const candidateFeedEl    = $('candidate-feed');
    const adminStatusEl      = $('admin-status');
    const candidateStatusEl  = $('candidate-status');
    const adminFeedLabel     = $('admin-feed-label');
    const candidateFeedLabel = $('candidate-feed-label');
    const btnCopyInvite      = $('btn-copy-invite');
    const tabIntelBtn        = $('tab-intel-btn');

    if (localRole === 'candidate') {
        if (btnCopyInvite) btnCopyInvite.style.display = 'none';
        if (tabIntelBtn)   tabIntelBtn.style.display   = 'none';
    }

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
        if (message.includes('Failed to fetch')) return;

        const colors = { system: 'text-white/40', audio: 'text-cyan-400', video: 'text-purple-400', error: 'text-red-400' };
        const empty = logList.querySelector('[data-empty]');
        if (empty) empty.remove();

        const el = document.createElement('div');
        el.className = `${colors[type] || colors.system} flex items-start gap-2`;
        el.innerHTML = `<span class="text-white/20 shrink-0">${new Date().toLocaleTimeString('en', { hour12: false })}</span>${message}`;
        logList.appendChild(el);
        logList.scrollTop = logList.scrollHeight;
    }

    // ── Verification Manager (Gatekeeper) ─────────────────────────────────────
    window.VerificationManager = {
        stream: null,
        recorder: null,
        chunks: [],
        requestId: null,
        roomName: null,
        participantName: null,

        async init(requestId, roomName, participantName) {
            this.requestId = requestId;
            this.roomName = roomName;
            this.participantName = participantName;
            
            $('verification-overlay')?.classList.remove('hidden');
            
            const recordBtn = $('btn-verify-record');
            if (recordBtn) {
                const newBtn = recordBtn.cloneNode(true);
                recordBtn.parentNode.replaceChild(newBtn, recordBtn);
                newBtn.addEventListener('click', () => this.startRecording());
            }
            
            try {
                this.stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                const preview = $('verify-video-preview');
                if (preview) preview.srcObject = this.stream;
                if (window.lucide) window.lucide.createIcons();
            } catch (err) {
                console.error("Camera access failed:", err);
                showToast("Camera access required for verification", "error");
            }
        },

        async startRecording() {
            if (!this.stream) {
                showToast("No camera stream found. Please refresh.", "error");
                return;
            }
            
            const btn = $('btn-verify-record');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="animate-pulse">RECORDING...</span>';
            }

            $('verify-countdown-overlay')?.classList.remove('hidden');
            let timeLeft = 10;
            const countdownEl = $('verify-countdown');
            if (countdownEl) countdownEl.textContent = timeLeft;
            
            this.chunks = [];
            this.recorder = new MediaRecorder(this.stream);
            this.recorder.ondataavailable = (e) => this.chunks.push(e.data);
            this.recorder.onstop = () => this.uploadVideo();
            this.recorder.start();

            const timer = setInterval(() => {
                timeLeft--;
                if (countdownEl) countdownEl.textContent = timeLeft;
                if (timeLeft <= 0) {
                    clearInterval(timer);
                    this.recorder.stop();
                    $('verify-countdown-overlay')?.classList.add('hidden');
                }
            }, 1000);
        },

        async uploadVideo() {
            $('verify-processing-overlay')?.classList.remove('hidden');
            const blob = new Blob(this.chunks, { type: 'video/webm' });
            const formData = new FormData();
            formData.append('file', blob);

            try {
                const res = await fetch(`${API_BASE}/api/verify-candidate/${this.requestId}`, {
                    method: 'POST',
                    body: formData
                });
                
                if (res.ok) {
                    const result = await res.json();
                    $('verify-status-text').textContent = "Verification Uploaded Successfully";
                    setTimeout(() => {
                        $('verification-overlay')?.classList.add('hidden');
                        this.stopStream();
                        showToast("Verification submitted. Waiting for AI analysis.", "success");
                    }, 2000);
                } else {
                    throw new Error("Upload failed");
                }
            } catch (err) {
                console.error("Verification upload failed:", err);
                $('verify-status-text').textContent = "Upload Failed. Try Again.";
                const btn = $('btn-verify-record');
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<i data-lucide="rotate-ccw" class="w-4 h-4"></i> Retry Verification';
                    if (window.lucide) window.lucide.createIcons({ nodes: [btn] });
                }
            }
        },

        stopStream() {
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }
        }
    };

    // ── Timer ─────────────────────────────────────────────────────────────────
    function startTimer(initialSeconds) {
        sessionSeconds = initialSeconds;
        if (timerInterval) clearInterval(timerInterval);
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
                .select('created_at, max_duration_mins, scheduled_at')
                .eq('room_id', roomId)
                .single();

            if (error) throw error;
            return data;
        } catch (e) {
            console.warn("[RoomMeta] Falling back to default limits:", e);
            return { created_at: new Date().toISOString(), max_duration_mins: 10, scheduled_at: null };
        }
    }

    // ── Feed management ───────────────────────────────────────────────────────
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

    // ── Dynamic Video Grid Layout ─────────────────────────────────────────────
    function updateGrid(count) {
        if (!remoteArea) return;
        remoteArea.style.display = 'grid';
        remoteArea.style.gap = '12px';
        remoteArea.style.width = '100%';
        remoteArea.style.height = '100%';

        if (count <= 1) {
            remoteArea.style.gridTemplateColumns = '1fr';
            remoteArea.style.gridTemplateRows = '1fr';
        } else if (count === 2) {
            remoteArea.style.gridTemplateColumns = '1fr 1fr';
            remoteArea.style.gridTemplateRows = '1fr';
        } else if (count === 3) {
            remoteArea.style.gridTemplateColumns = '1fr 1fr';
            remoteArea.style.gridTemplateRows = '1fr 1fr';
        } else {
            remoteArea.style.gridTemplateColumns = '1fr 1fr';
            remoteArea.style.gridTemplateRows = `repeat(${Math.ceil(count / 2)}, 1fr)`;
        }
    }

    // ── Remote participant video panel ────────────────────────────────────────
    // CHANGED: added <canvas> overlay inside each panel
    function createParticipantPanel(identity, name, role) {
        if (remotePlaceholder) remotePlaceholder.classList.add('hidden');

        const panel = document.createElement('div');
        panel.id = `panel-${identity}`;
        panel.className = 'relative w-full h-full flex items-center justify-center bg-black rounded-[2rem] overflow-hidden transition-all min-h-0';
        panel.setAttribute('data-identity', identity);

        const videoSlot = document.createElement('div');
        videoSlot.id = `video-slot-${identity}`;
        videoSlot.className = 'absolute inset-0';
        panel.appendChild(videoSlot);

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

        // ── NEW: forensic canvas overlay ──────────────────────────────────────
        const overlayCanvas = document.createElement('canvas');
        overlayCanvas.id = `canvas-${identity}`;
        overlayCanvas.style.cssText = [
            'position:absolute',
            'inset:0',
            'width:100%',
            'height:100%',
            'pointer-events:none',
            'z-index:5',
        ].join(';');
        panel.appendChild(overlayCanvas);
        // ─────────────────────────────────────────────────────────────────────

        const label = document.createElement('div');
        label.className = 'absolute bottom-3 left-3 px-3 py-1 bg-black/60 backdrop-blur-xl rounded-lg text-[9px] font-mono uppercase tracking-widest border border-white/5 z-10';
        label.innerHTML = `<span class="text-cyan-400 font-bold mr-2">●</span><span>${name || identity}</span>`;
        panel.appendChild(label);

        const ring = document.createElement('div');
        ring.id = `ring-${identity}`;
        ring.className = 'absolute inset-0 rounded-[2rem] border-2 border-cyan-400 opacity-0 transition-opacity duration-200 pointer-events-none z-10';
        panel.appendChild(ring);

        remoteArea.appendChild(panel);

        const count = remoteArea.querySelectorAll('[data-identity]').length;
        updateGrid(count);

        return panel;
    }

    function removeParticipantPanel(identity) {
        const panel = $(`panel-${identity}`);
        if (panel) panel.remove();

        const remaining = remoteArea.querySelectorAll('[data-identity]');
        if (remotePlaceholder && remaining.length === 0) {
            remotePlaceholder.classList.remove('hidden');
            remoteArea.style.display = '';
        } else {
            updateGrid(remaining.length);
        }
    }

    // ── Update control button visual state ───────────────────────────────────
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

        if (joinLobby) joinLobby.style.display = 'none';

        if (connectionBadge) {
            connectionBadge.textContent = 'LIVE';
            connectionBadge.className = 'text-[9px] font-mono px-3 py-1 rounded-full bg-cyan-400/10 border border-cyan-400/30 text-cyan-400 uppercase tracking-widest animate-pulse';
        }

        const localLabel = $('local-label');
        if (localLabel) localLabel.textContent = participantName;

        setFeedLabel(role, participantName);
        setFeedStatus(role, 'LIVE', true);

        addLog(`Connected to room: ${roomName} as ${role.toUpperCase()}`);

        fetchRoomMeta(roomName).then(meta => {
            const createdAt = new Date(meta.created_at).getTime();
            const now = Date.now();
            const totalDuration = meta.duration_seconds || 600;
            const elapsed = Math.floor((now - createdAt) / 1000);
            const remaining = totalDuration - elapsed;

            if (remaining <= 0) {
                showToast("SESSION HAS EXPIRED.", "error");
                timerEl.textContent = "00:00";
                setTimeout(() => { window.endSession?.(); }, 2000);
            } else {
                startTimer(remaining);
                addLog(`Session active. ${Math.floor(remaining / 60)}m ${remaining % 60}s remaining.`, 'system');
            }
        });

        showToast(`Connected as ${participantName}`, 'success');

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

        setFeedStatus('hr', 'OFFLINE', false);
        setFeedStatus('candidate', 'OFFLINE', false);

        addLog('Session terminated by server', 'error');

        const overlay = $('termination-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
            if (window.lucide) window.lucide.createIcons({ nodes: [overlay] });

            setTimeout(() => {
                overlay.classList.remove('opacity-0');
                overlay.classList.add('opacity-100');
            }, 50);
        } else {
            showToast('Session ended', 'error');
            setTimeout(() => { window.location.href = 'index.html'; }, 2000);
        }
    });

    // ── FIX 2: Single endSession with full HR termination logic ──────────────
    window.endSession = async function() {
        showToast("TERMINATING CONNECTION...", "info");

        if (localRole === 'hr' || localRole === 'admin') {
            try {
                const { data: { session } } = await supabase.auth.getSession();
                const authHeader = session ? `Bearer ${session.access_token}` : null;

                if (authHeader && currentRoomId) {
                    // Temporarily disable global termination so the candidate isn't kicked if HR simply leaves
                    // To completely destroy the room, a dedicated "End Interview for All" button should be used instead.
                    /*
                    await fetch(`${API_BASE}/api/livekit/room/${currentRoomId}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': authHeader }
                    });

                    await fetch(`${API_BASE}/api/nodes/${currentRoomId}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': authHeader }
                    });
                    */
                }
            } catch (e) {
                console.error("Failed to execute global termination protocol:", e);
            }

            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 800);
        } else {
            window.LiveKitSession?.disconnect();
        }
    };

    $('btn-leave')?.addEventListener('click', () => {
        window.endSession();
    });

    window.addEventListener('lk:participant-joined', (e) => {
        const { identity, name, role } = e.detail;
        addLog(`${name} joined as ${role.toUpperCase()}`, 'audio');
        showToast(`${name} joined`, 'success');

        createParticipantPanel(identity, name, role);

        setFeedLabel(role, name);
        setFeedStatus(role, 'CONNECTED', true);
    });

    window.addEventListener('lk:participant-left', (e) => {
        const { identity, name } = e.detail;
        addLog(`${name} left the session`, 'system');
        showToast(`${name} disconnected`, 'error');
        removeParticipantPanel(identity);
    });

    // CHANGED: save candidateIdentity when candidate video arrives
    window.addEventListener('lk:participant-video', (e) => {
        const { identity, name, role, element, action } = e.detail;

        if (action === 'add' && element) {
            const slot    = $(`video-slot-${identity}`);
            const waiting = $(`waiting-${identity}`);
            if (slot) {
                slot.appendChild(element);
                element.className = 'w-full h-full object-cover';
            }
            if (waiting) waiting.classList.add('hidden');
            addLog(`Video stream from ${name}`, 'video');
        }

        if (action === 'remove') {
            const slot    = $(`video-slot-${identity}`);
            const waiting = $(`waiting-${identity}`);
            if (slot) slot.innerHTML = '';
            if (waiting) waiting.classList.remove('hidden');
            if (role === 'candidate') {
                candidateVideo    = null;
                candidateIdentity = null;   // ← clear identity too
                stopForensicEngine();
            }
        }

        // Auto-start forensic engine for HR when candidate video arrives
        if (action === 'add' && role === 'candidate' && (localRole === 'hr' || localRole === 'admin')) {
            candidateVideo    = element;
            candidateIdentity = identity;   // ← save identity
            startForensicEngine();
        }
    });

    window.addEventListener('lk:speaking-changed', (e) => {
        const { speakers } = e.detail;

        remoteArea.querySelectorAll('[id^="ring-"]').forEach(ring => {
            ring.style.opacity = '0';
        });

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
        if (localVideo) localVideo.style.opacity = camEnabled ? '1' : '0';
    });

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

        if (msg.includes('expired') || msg.includes('انتهت صلاحيته')) {
            if (joinLobby) {
                joinLobby.innerHTML = `
                    <div class="relative mb-10">
                        <div class="absolute -inset-16 bg-white/5 rounded-full blur-3xl"></div>
                        <div class="w-32 h-32 rounded-full border-2 border-white/5 bg-white/5 backdrop-blur-sm flex items-center justify-center">
                            <i data-lucide="link-2-off" class="w-12 h-12 text-white/20"></i>
                        </div>
                    </div>
                    <div class="text-center px-10">
                        <h3 class="text-2xl font-black uppercase tracking-tight mb-3 text-white/80">
                            انتهت صلاحية الرابط
                        </h3>
                        <p class="text-[11px] font-mono text-white/40 uppercase tracking-[0.2em] max-w-sm mx-auto leading-loose">
                            This session has already ended or been terminated by the host.
                        </p>
                        <div class="mt-10">
                            <a href="index.html" class="px-8 py-3 bg-white/5 border border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-white text-white hover:text-obsidian transition-all">
                                العودة للرئيسية
                            </a>
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

    // ── Forensic Lexical Engine Integration ──────────────────────────────────
    async function analyzeLexical(text) {
        if (!text) return;
        const wordCount = text.trim().split(/\s+/).length;
        
        // ── Word Density Update ──────────────────────────────────────────────
        const wordDensityEl = $('wordDensity');
        if (wordDensityEl) {
            const wpm = (wordCount / (text.length / 50)).toFixed(1); // Rough WPM estimate
            wordDensityEl.textContent = `${wpm} wpm`;
        }

        // 🛡️ Filter short sentences to prevent inaccurate results
        if (text.trim().length < 20) {
            const lexicalStatus = $('lexicalStatus');
            if (lexicalStatus) {
                lexicalStatus.textContent = 'Collecting more data...';
                lexicalStatus.className = 'text-[8px] text-white/30 font-mono uppercase tracking-[0.2em] px-2 py-0.5 bg-white/5 rounded';
            }
            return; 
        }

        const lexicalStatus = $('lexicalStatus');
        const lexAIProb      = $('lexAIProb');
        const nlpConf        = $('nlpConf');
        const nlpConfFill    = $('nlpConfFill');
        const patternMatch   = $('patternMatch');
        const lexPulse       = $('lexicalPulse');

        try {
            if (lexicalStatus) {
                lexicalStatus.textContent = 'Neural Scanning...';
                lexicalStatus.className = 'text-[8px] text-cyan-400/60 font-mono uppercase tracking-[0.2em] px-2 py-0.5 bg-cyan-400/10 rounded animate-pulse';
            }
            if (lexPulse) lexPulse.className = 'w-1.5 h-1.5 bg-cyan-400 rounded-full animate-ping';
            
            // 📡 Dynamic Drift Simulation (makes it feel alive)
            const driftVal = $('driftVal');
            if (driftVal) {
                const randomDrift = (Math.random() * 0.005).toFixed(4);
                driftVal.textContent = `±${randomDrift}`;
            }

            const response = await fetch(`${window.APP_CONFIG.nlpUrl}/analyze-forensics`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });

            if (!response.ok) throw new Error('Lexical Engine Offline');

            const result = await response.json();
            const prob = result.overall_ai_probability || 0;

            // Check text length to avoid false positives on short sentences
            const wordCount = text.split(' ').filter(w => w.length > 0).length;
            if (wordCount < 4) {
                if (lexicalStatus) {
                    lexicalStatus.innerHTML = `<span class="text-orange-400">SHORT SENTENCE</span>`;
                    lexicalStatus.className = 'text-[9px] font-mono uppercase tracking-[0.2em] px-2 py-0.5 bg-orange-400/10 rounded border border-orange-400/20';
                }
                if (patternMatch) patternMatch.textContent = "INSUFFICIENT_DATA";
                return; // Not enough data for NLP
            }

            // Confidence Level (based on text length - longer is more confident)
            const confidence = Math.min(0.98, 0.4 + (wordCount / 50)).toFixed(2);
            if (nlpConf) nlpConf.textContent = confidence;
            if (nlpConfFill) nlpConfFill.style.width = `${confidence * 100}%`;

            // Update UI with clear Verdict
            if (lexicalStatus) {
                if (prob < 0.3) {
                    lexicalStatus.innerHTML = `<span class="text-green-400 font-black"><i data-lucide="user-check" class="w-3 h-3 inline pb-0.5"></i> HUMAN</span>`;
                    lexicalStatus.className = 'text-[10px] font-mono uppercase tracking-[0.2em] px-2 py-0.5 bg-green-400/10 rounded border border-green-400/20';
                } else if (prob > 0.7) {
                    lexicalStatus.innerHTML = `<span class="text-red-400 font-black"><i data-lucide="bot" class="w-3 h-3 inline pb-0.5"></i> AI GENERATED</span>`;
                    lexicalStatus.className = 'text-[10px] font-mono uppercase tracking-[0.2em] px-2 py-0.5 bg-red-400/10 rounded border border-red-400/20';
                } else {
                    lexicalStatus.innerHTML = `<span class="text-yellow-400 font-black">UNCERTAIN</span>`;
                    lexicalStatus.className = 'text-[10px] font-mono uppercase tracking-[0.2em] px-2 py-0.5 bg-yellow-400/10 rounded border border-yellow-400/20';
                }
                lucide.createIcons({ nodes: [lexicalStatus] });
            }

            if (patternMatch) {
                const patterns = ["SYNTACTIC_FLOW", "LEXICAL_DENSITY", "SEMANTIC_DRIFT", "NEURAL_SIGNATURE", "PROBABILISTIC_DECAY"];
                patternMatch.textContent = patterns[Math.floor(prob * (patterns.length - 1))] || patterns[0];
            }

            if (lexAIProb) {
                const probPercent = (prob * 100).toFixed(1);
                lexAIProb.textContent = `${probPercent}%`;
                lexAIProb.className = prob > 0.7 
                    ? 'text-lg font-black text-red-500 leading-none' 
                    : prob > 0.4
                        ? 'text-lg font-black text-yellow-400 leading-none'
                        : 'text-lg font-black text-green-400 leading-none';
            }

            // Impact Overall Integrity Score
            const scoreEl = $('scoreBig');
            const scoreFill = $('scoreFill');
            if (scoreEl && prob > 0.5) {
                // If high AI probability, it significantly lowers the integrity score
                const currentScore = parseInt(scoreEl.textContent) || 100;
                const newScore = Math.max(0, currentScore - (prob * 20));
                scoreEl.innerHTML = `${Math.round(newScore)}<span class="text-cyan-400">%</span>`;
                if (scoreFill) scoreFill.style.width = `${newScore}%`;
            }

            if (lexPulse) lexPulse.className = 'w-1.5 h-1.5 bg-white/10 rounded-full';

            if (prob > 0.8) {
                showToast('🚨 High AI Lexical Pattern Detected!', 'error');
                addForensicLog(`LEXICAL ALERT: ${result.verdict}`, 'error');
            }

        } catch (err) {
            console.warn('[Forensic] Lexical engine error:', err);
            if (lexicalStatus) {
                lexicalStatus.textContent = 'Engine Offline';
                lexicalStatus.className = 'text-[8px] text-white/20 font-mono uppercase tracking-[0.2em] px-2 py-0.5 bg-white/5 rounded';
            }
            if (lexPulse) lexPulse.className = 'w-1.5 h-1.5 bg-white/10 rounded-full';
        }
    }

    async function saveLogToServer(sender, message) {
        // Use currentRoomId from URL params (line 30) — reliable, doesn't depend on LiveKitSession state
        const roomId = currentRoomId || window.LiveKitSession?.getState?.()?.roomName;
        if (!roomId || !message?.trim()) return;

        try {
            const { data: { session } } = await supabase.auth.getSession();
            const token = session?.access_token;
            const apiBase = window.APP_CONFIG?.backendUrl || 'http://127.0.0.1:8000';

            const resp = await fetch(`${apiBase}/api/logs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({
                    node_id: roomId,
                    sender:  sender,
                    message: message
                })
            });

            if (!resp.ok) {
                const errText = await resp.text();
                console.warn('[Log] Backend rejected log:', resp.status, errText);
            }
        } catch (err) {
            console.warn('[Log] Failed to save transcript:', err);
        }
    }

    // ── AI Agent Logic ────────────────────────────────────────────────────────
    let isAgentThinking = false;

    async function callAiAgent(speakerRole, text) {
        if (!aiAgentActive || isAgentThinking) return;
        
        // Primary analysis for HR/Admin users only
        if (localRole !== 'hr' && localRole !== 'admin') return;

        isAgentThinking = true;
        const statusText = $('agent-status-text');
        if (statusText) statusText.textContent = "Neural Analysis...";

        try {
            // Get session token (Supabase global in integra-session.html)
            const { data: { session } } = await window.supabase.auth.getSession();
            const token = session?.access_token;

            // Load LLM Config from Storage
            let llmConfig = {};
            try {
                llmConfig = JSON.parse(localStorage.getItem("INTEGRA_LLM_CONFIG") || "{}");
            } catch (e) {}

            // Context-aware Prompting
            const speakerLabel = speakerRole === 'hr' ? 'HR (Interviewer)' : 'Candidate';
            const prompt = `[INTERVIEW TRANSCRIPT]\nSpeaker: ${speakerLabel}\nText: "${text}"\n\nTask: Analyze this input. If it's a candidate's answer, highlight a strength or potential red flag. If it's an HR question, suggest a follow-up or provide context. Return exactly 2-3 short, professional bullet points for the dashboard.`;

            const response = await fetch(`${API_BASE}/api/agent/chat`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    prompt: prompt,
                    config: {
                        ...llmConfig,
                        systemPrompt: `[FAST_SYNC_PROTOCOL]
- ROLE: Real-time Neural Copilot.
- STYLE: Extremely short, telegraphic insights.
- FORMAT: 2-3 points. Max 5 words per point.
- NO REASONING: Go directly to insights.
- NO SKIP: Even for small talk, give a meta-comment (e.g., "Building rapport", "Candidate relaxed").
- SPEED: Respond in < 500ms.`
                    }
                })
            });

            const data = await response.json();
            if (response.ok && data.response) {
                // Remove any technical markers the LLM might still include
                let cleanRes = data.response.replace(/Thought:|Final Answer:|Action:|Action Input:/gi, "").trim();
                updateAgentSuggestions(cleanRes);
            }
        } catch (err) {
            console.error("[Agent] Link Failed:", err);
        } finally {
            isAgentThinking = false;
            if (statusText) statusText.textContent = "Active & Monitoring";
        }
    }

    function updateAgentSuggestions(response) {
        const container = $('agent-suggestions');
        if (!container) return;

        const suggestions = response.split('\n')
            .filter(line => line.trim())
            .map(line => line.replace(/^[*-]\s*/, '').trim());

        // Neural Pulse Update
        const statusText = $('agent-status-text');
        if (statusText) {
            statusText.innerHTML = `<span class="flex items-center gap-2"><span class="relative flex h-2 w-2"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span></span> Analysis Synced</span>`;
        }

        container.innerHTML = '';
        container.className = "flex flex-col gap-2 p-1 overflow-y-auto max-h-[160px]"; 

        suggestions.forEach((s, i) => {
            const el = document.createElement('div');
            el.className = "glass-panel px-4 py-2.5 rounded-xl border border-white/5 animate-slide-up shadow-sm hover:bg-white/10 transition-colors";
            el.style.animationDelay = `${i * 100}ms`;
            el.innerHTML = `
                <div class="flex items-start gap-2.5">
                    <div class="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0 shadow-[0_0_8px_rgba(34,211,238,0.4)]"></div>
                    <span class="text-[11px] text-gray-200 font-medium leading-relaxed">${s}</span>
                </div>
            `;
            container.appendChild(el);
        });
    }

    window.addEventListener('stt:final', (e) => {
        const state  = window.LiveKitSession?.getState?.();
        const myRole = state?.localRole || localRole;
        const myName = e.detail.name || state?.participantName || 'User';

        appendTranscription(myRole, e.detail.text, true);
        saveLogToServer(myName, e.detail.text);

        // 🔍 Agent Analysis for HR speech
        if (aiAgentActive && (myRole === 'hr' || myRole === 'admin')) {
            callAiAgent('hr', e.detail.text);
        }

        // 🔍 Only analyze if I am the candidate (for self-monitoring) 
        if (myRole === 'candidate') {
            analyzeLexical(e.detail.text);
        }
    });

    window.addEventListener('stt:interim', (e) => {
        const myRole = window.LiveKitSession?.getState?.()?.localRole || localRole;
        appendTranscription(myRole, e.detail.text, false);
    });

    window.addEventListener('lk:transcription', (e) => {
        const { role, text, isFinal, name } = e.detail;
        appendTranscription(role, text, isFinal);

        if (isFinal) {
            saveLogToServer(name || role.toUpperCase(), text);

            // 🔍 HR/Admin analyzes remote candidate transcriptions
            const myRole = window.LiveKitSession?.getState?.()?.localRole || localRole;
            
            if (role === 'candidate' && (myRole === 'hr' || myRole === 'admin')) {
                // Agent Analysis
                if (aiAgentActive) {
                    callAiAgent('candidate', text);
                }
                // Standard Lexical analysis
                analyzeLexical(text);
            }
        }
    });

    // ── Control Buttons ───────────────────────────────────────────────────────
    $('btn-toggle-mic')?.addEventListener('click', async () => {
        await window.LiveKitSession?.toggleMic();
    });

    $('btn-toggle-cam')?.addEventListener('click', async () => {
        await window.LiveKitSession?.toggleCamera();
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
    const audioBars = $('audio-bars');
    if (audioBars) {
        const BAR_COUNT = 32;
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
            }, 125);
        }

        function stopBarAnimation() {
            clearInterval(barInterval);
            barInterval = null;
        }

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                stopBarAnimation();
            } else {
                startBarAnimation();
            }
        });

        startBarAnimation();
    }

    // ── Local camera preview ──────────────────────────────────────────────────
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

    // ── Join Session Function ─────────────────────────────────────────────────
    window.joinSession = async function() {
        const btn       = $('btn-join');
        const inputRoom = document.getElementById('input-room');
        const inputName = document.getElementById('input-name');
        const inputRole = document.getElementById('input-role');

        const roomName = inputRoom ? inputRoom.value.trim() : new URLSearchParams(window.location.search).get('room');
        const name     = inputName ? inputName.value.trim() : new URLSearchParams(window.location.search).get('name');
        const role     = inputRole ? inputRole.value.trim() : (new URLSearchParams(window.location.search).get('role') || 'candidate');

        if (!roomName) {
            showToast("Missing Room ID", "error");
            return;
        }

        const meta = await fetchRoomMeta(roomName);
        if (meta && meta.scheduled_at) {
            const scheduledAt = new Date(meta.scheduled_at);
            const now = new Date();
            const buffer = 5 * 60 * 1000;

            if (scheduledAt > (now.getTime() + buffer)) {
                const diff = scheduledAt - now;
                const minutes = Math.floor(diff / 60000);
                showToast(`الموعد لم يحن بعد. يمكنك الدخول قبل 5 دقائق (مبقي ${minutes} دقيقة)`, "info");
                if (btn) {
                    btn.disabled = true;
                    btn.textContent = `متبقي ${minutes} دقيقة`;
                    setTimeout(() => { btn.disabled = false; window.joinSession(); }, Math.min(diff - buffer, 30000));
                }
                return;
            }
        }

        if (btn) {
            btn.disabled = true;
            btn.textContent = 'CONNECTING...';
        }

        try {
            const result = await window.LiveKitSession.connect({
                roomName: roomName,
                participantName: name,
                role: role
            });

            if (result && (result.status === "AWAITING_APPROVAL" || result.liveness_status === "PENDING")) {
                // If Deepfake verification is required
                if (result.liveness_status === "PENDING") {
                    window.VerificationManager.init(result.request_id, roomName, name);
                }

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
                            <h3 class="text-xl font-black uppercase tracking-widest mb-3 text-white">
                                ${result.liveness_status === 'PENDING' ? 'Identity Verification Required' : 'الطلب قيد الانتظار'}
                            </h3>
                            <p class="text-[11px] font-mono text-white/40 uppercase tracking-[0.2em] max-w-sm mx-auto leading-relaxed">
                                ${result.message_en || 'Please wait for identity verification and host approval.'}
                            </p>
                            <div class="mt-8 py-3 px-6 bg-white/5 rounded-full inline-flex items-center gap-3 border border-white/5">
                                <span class="w-2 h-2 ${result.liveness_status === 'PENDING' ? 'bg-amber-500' : 'bg-cyan-500'} rounded-full animate-ping"></span>
                                <span class="text-[9px] font-black ${result.liveness_status === 'PENDING' ? 'text-amber-400' : 'text-cyan-400'} uppercase tracking-widest">
                                    ${result.liveness_status === 'PENDING' ? 'Action Required: Verification' : 'Verifying Identity...'}
                                </span>
                            </div>
                        </div>
                    `;
                    lucide.createIcons({ nodes: [joinLobby] });
                }

                let pollDelay = 3000;
                if (window._pollStatusInterval) clearTimeout(window._pollStatusInterval);
                
                const pollRequestStatus = async () => {
                    try {
                        const checkRaw = await fetch(`${API_BASE}/api/livekit/request-status?room_id=${roomName}&participant_name=${name}`);
                        if (!checkRaw.ok) {
                            pollDelay = Math.min(pollDelay * 1.5, 15000);
                            window._pollStatusInterval = setTimeout(pollRequestStatus, pollDelay);
                            return;
                        }
                        
                        const check = await checkRaw.json();

                        // 1. Check for Deepfake Failure
                        if (check.liveness_status === "FAILED") {
                            window._pollStatusInterval = null;
                            showToast("Deepfake detected! Verification failed.", "error");
                            if (joinLobby) {
                                joinLobby.innerHTML = `
                                    <div class="text-center">
                                        <i data-lucide="alert-octagon" class="w-16 h-16 text-red-500 mx-auto mb-4"></i>
                                        <h3 class="text-red-500 font-black uppercase tracking-widest">Identity Fraud Detected</h3>
                                        <p class="text-xs text-white/40 mt-2">Verification system has flagged this session.</p>
                                    </div>
                                `;
                                lucide.createIcons({ nodes: [joinLobby] });
                            }
                            return;
                        }

                        // 2. Check for Approval
                        if (check.status === "APPROVED" && check.liveness_status !== "PENDING") {
                            window._pollStatusInterval = null;
                            window.joinSession();
                        } else if (check.status === "REJECTED") {
                            window._pollStatusInterval = null;
                            showToast("تم رفض طلب الدخول | Entry rejected", "error");
                            if (joinLobby) {
                                joinLobby.innerHTML = `<h3 class="text-red-500 font-bold uppercase">Entry Rejected</h3>`;
                            }
                        } else {
                            // Still PENDING, exponential backoff
                            pollDelay = Math.min(pollDelay * 1.5, 15000);
                            window._pollStatusInterval = setTimeout(pollRequestStatus, pollDelay);
                        }
                    } catch (e) {
                        console.error("Polling error:", e);
                        pollDelay = Math.min(pollDelay * 1.5, 15000);
                        window._pollStatusInterval = setTimeout(pollRequestStatus, pollDelay);
                    }
                };
                
                pollRequestStatus();
                return;
            }

            if (meta) {
                const startTime = new Date(meta.created_at).getTime();
                const now = new Date().getTime();
                const elapsedSeconds = Math.floor((now - startTime) / 1000);
                const totalAllowedSeconds = (meta.max_duration_mins || 10) * 60;
                const remainingSeconds = totalAllowedSeconds - elapsedSeconds;

                console.log(`[Timer] Total: ${totalAllowedSeconds}s, Elapsed: ${elapsedSeconds}s, Remaining: ${remainingSeconds}s`);
                startTimer(remainingSeconds);
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

    if (logList) {
        logList.innerHTML = '';
        addLog('System initialized. Awaiting session...');
    }

    // ── HR Lobby Monitor ──────────────────────────────────────────────────────
    if (localRole === 'hr' || localRole === 'interviewer') {
        const lobbyContainer = document.createElement('div');
        lobbyContainer.id = 'hr-lobby-notifs';
        lobbyContainer.className = 'fixed top-20 right-6 w-80 space-y-4 z-[9999]';
        document.body.appendChild(lobbyContainer);

        const knownRequests = new Set();

        let hrPollDelay = 5000;
        async function startSmartMonitoring() {
            const meta = await fetchRoomMeta(currentRoomId);
            const scheduledAt = meta?.scheduled_at ? new Date(meta.scheduled_at) : null;

            const checkLogic = async () => {
                if (!currentRoomId) return;
                const now = new Date();

                if (scheduledAt) {
                    const diff = scheduledAt - now;
                    const fiveMins = 5 * 60 * 1000;
                    if (diff > fiveMins) {
                        console.log(`[HR Monitor] Too early. Check-back in 1 min. Remaining: ${Math.round(diff / 60000)}m`);
                        setTimeout(startSmartMonitoring, 60000);
                        return;
                    }
                }

                try {
                    const res = await fetch(`${API_BASE}/api/livekit/pending-requests/${currentRoomId}`);
                    if (res.ok) {
                        const requests = await res.json();
                        
                        // If there are pending requests, we poll faster. Otherwise, exponential backoff.
                        if (requests.length > 0) {
                            hrPollDelay = 5000; // reset to 5s if there is activity
                        } else {
                            hrPollDelay = Math.min(hrPollDelay * 1.2, 20000); // Backoff up to 20s
                        }

                        requests.forEach(req => {
                            const reqKey = `${req.participant_name}`;
                            let card = document.getElementById(`lobby-card-${req.id}`);
                            
                            if (card) {
                                // Update existing card status if changed
                                const badge = card.querySelector('.liveness-badge');
                                if (badge) {
                                    const currentStatus = badge.getAttribute('data-status');
                                    if (currentStatus !== req.liveness_status) {
                                        badge.setAttribute('data-status', req.liveness_status || 'PENDING');
                                        badge.className = `liveness-badge text-[8px] font-black uppercase px-2 py-0.5 rounded border ${
                                            req.liveness_status === 'VERIFIED' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 
                                            req.liveness_status === 'FAILED' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 
                                            req.liveness_status === 'VERIFYING' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse' :
                                            'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                        }`;
                                        badge.innerHTML = `Gatekeeper: ${req.liveness_status || 'PENDING'}`;
                                        
                                        // Optionally update button state
                                        const approveBtn = card.querySelector('.btn-approve');
                                        if (req.liveness_status !== 'VERIFIED') {
                                            approveBtn.classList.add('opacity-50', 'cursor-not-allowed');
                                            approveBtn.title = "تحذير: لم يتم التحقق من هوية المرشح بعد";
                                        } else {
                                            approveBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                                            approveBtn.title = "تم التحقق بنجاح";
                                        }
                                    }
                                }
                                return;
                            }

                            const newCard = document.createElement('div');
                            newCard.id = `lobby-card-${req.id}`;
                            newCard.className = 'bg-obsidian/90 backdrop-blur-xl border border-white/10 p-5 rounded-2xl shadow-2xl animate-[slideIn_0.3s_ease-out] ring-1 ring-white/5';
                            newCard.innerHTML = `
                                <div class="flex items-start gap-4 mb-4">
                                    <div class="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center border border-cyan-500/30">
                                        <i data-lucide="user-plus" class="w-5 h-5 text-cyan-400"></i>
                                    </div>
                                    <div class="flex-1">
                                        <h4 class="text-[11px] font-black text-white uppercase tracking-widest mb-1">طلب انضمام جديد</h4>
                                        <p class="text-[13px] font-bold text-white/90">${req.participant_name}</p>
                                        
                                        <!-- Deepfake Verification Badge -->
                                        <div class="mt-2 flex items-center gap-2">
                                            <span data-status="${req.liveness_status || 'PENDING'}" class="liveness-badge text-[8px] font-black uppercase px-2 py-0.5 rounded border ${
                                                req.liveness_status === 'VERIFIED' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 
                                                req.liveness_status === 'FAILED' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 
                                                req.liveness_status === 'VERIFYING' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse' :
                                                'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                            }">
                                                Gatekeeper: ${req.liveness_status || 'PENDING'}
                                            </span>
                                        </div>
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

                            lobbyContainer.appendChild(newCard);
                            if (window.lucide) window.lucide.createIcons({ scope: newCard });

                            newCard.querySelector('.btn-approve').onclick = async () => {
                                if (req.liveness_status !== 'VERIFIED') {
                                    if (!confirm("⚠️ تنبيه أمني: هذا المرشح لم يجتز اختبار الـ Deepfake أو لا يزال قيد الفحص. هل تريد السماح له بالدخول على مسؤوليتك؟")) {
                                        return;
                                    }
                                }
                                await fetch(`${API_BASE}/api/livekit/decide-request`, {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ room_id: currentRoomId, participant_name: req.participant_name, decision: 'APPROVED' })
                                });
                                newCard.remove();
                            };

                            newCard.querySelector('.btn-deny').onclick = async () => {
                                await fetch(`${API_BASE}/api/livekit/decide-request`, {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ room_id: currentRoomId, participant_name: req.participant_name, decision: 'REJECTED' })
                                });
                                newCard.remove();
                                knownRequests.delete(reqKey);
                            };

                            lobbyContainer.appendChild(card);
                            lucide.createIcons({ nodes: [card] });
                        });
                    } else {
                        hrPollDelay = Math.min(hrPollDelay * 1.2, 20000);
                    }
                } catch (e) { 
                    console.error("Lobby check failed:", e); 
                    hrPollDelay = Math.min(hrPollDelay * 1.5, 20000);
                }

                setTimeout(checkLogic, hrPollDelay);
            };

            checkLogic();
        }

        startSmartMonitoring();
    }

    // ── Copy Invite Link ──────────────────────────────────────────────────────
    window.copyInviteLink = function() {
        const inputRoom = document.getElementById('input-room');
        const room = inputRoom ? inputRoom.value.trim() : 'integra-room-01';
        const base = window.location.origin + window.location.pathname.replace('integra-session.html', '');
        const link = `${base}integra-session.html?room=${room}&role=candidate`;

        navigator.clipboard.writeText(link).then(() => {
            if (typeof showToast === 'function') showToast('Invite link copied!', 'success');
        });
    };

    // ── triggerCognitiveTest ──────────────────────────────────────────────────
    window.triggerCognitiveTest = function() {
        if (typeof showToast === 'function') showToast('Cognitive Challenge Protocol Initiated', 'info');
        addForensicLog("Cognitive Challenge Triggered", "warning");
    };

    // ── Forensic Engine ───────────────────────────────────────────────────────
    function startForensicEngine() {
        if (forensicWS || forensicInterval) return;

        console.log("[Forensics] Initializing Engine...");
        addForensicLog("Engine Initializing...", "system");

        // Use centralized config for Forensic WebSocket
        forensicWS = new WebSocket(window.APP_CONFIG.wsUrl);

        forensicWS.onopen = () => {
            console.log("[Forensics] WebSocket Connected");
            addForensicLog("Forensic Link Established", "success");

            const connBadge = $('connBadge');
            if (connBadge) {
                connBadge.textContent = 'ONLINE';
                connBadge.className = 'text-[9px] font-black px-2 py-1 bg-cyan-400/10 text-cyan-400 border border-cyan-400/20 rounded uppercase tracking-widest';
            }

            const statusChip = $('statusChip');
            if (statusChip) {
                statusChip.textContent = 'Safe';
                statusChip.className = 'text-[9px] font-black px-2 py-1 bg-green-500/10 text-green-500 border border-green-500/20 rounded uppercase tracking-widest';
            }
        };

        forensicWS.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                updateForensicUI(data);
            } catch (err) {
                console.error("[Forensics] Data Parse Error:", err);
            }
        };

        forensicWS.onerror = (err) => {
            console.error("[Forensics] WebSocket Error:", err);
            addForensicLog("Engine Link Error", "error");
        };

        forensicWS.onclose = () => {
            console.warn("[Forensics] WebSocket Closed");
            stopForensicEngine();
        };

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        forensicInterval = setInterval(() => {
            if (!candidateVideo || forensicWS.readyState !== WebSocket.OPEN) return;

            canvas.width  = 320;
            canvas.height = 240;
            ctx.drawImage(candidateVideo, 0, 0, canvas.width, canvas.height);

            canvas.toBlob((blob) => {
                if (blob && forensicWS.readyState === WebSocket.OPEN) {
                    forensicWS.send(blob);
                }
            }, 'image/jpeg', 0.5);
        }, 100);
    }

    function stopForensicEngine() {
        if (forensicInterval) clearInterval(forensicInterval);
        if (forensicWS) forensicWS.close();
        forensicInterval = null;
        forensicWS = null;
        addForensicLog("Engine Offline", "system");

        const connBadge = $('connBadge');
        if (connBadge) {
            connBadge.textContent = 'OFFLINE';
            connBadge.className = 'text-[9px] font-black px-2 py-1 bg-white/5 text-white/30 border border-white/10 rounded uppercase tracking-widest';
        }

        const statusChip = $('statusChip');
        if (statusChip) {
            statusChip.textContent = 'Standby';
            statusChip.className = 'text-[9px] font-black px-2 py-1 bg-white/5 text-white/30 border border-white/10 rounded uppercase tracking-widest';
        }
    }

    // ── NEW: Draw forensic overlay on candidate's canvas ─────────────────────
    function drawForensicCanvas(data) {
        if (!candidateIdentity) return;
        const canvas = $(`canvas-${candidateIdentity}`);
        if (!canvas || !candidateVideo) return;

        // Match canvas dimensions to the displayed video element
        canvas.width  = candidateVideo.videoWidth  || candidateVideo.clientWidth  || 640;
        canvas.height = candidateVideo.videoHeight || candidateVideo.clientHeight || 480;

        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const status = data.status || 'NO_FACE';
        const color  = status === 'FOCUSED'    ? '#22d3ee'   // cyan-400
                     : status === 'SUSPICIOUS' ? '#ffb800'   // amber
                                               : '#ff3535';  // red

        // The forensic engine receives 320x240 frames
        const scaleX = canvas.width / 320;
        const scaleY = canvas.height / 240;

        // Check if the video is mirrored (usually true for local participant preview)
        const transform = window.getComputedStyle(candidateVideo).transform;
        const isMirrored = transform !== 'none' && transform.includes('matrix(-1,') 
                        || candidateVideo.style.transform.includes('scaleX(-1)')
                        || (typeof localRole !== 'undefined' && localRole === 'candidate');

        const flipX = (x) => isMirrored ? (320 - x) * scaleX : x * scaleX;

        // ── BBox corner brackets ──────────────────────────────────────────────
        if (data.bbox) {
            const x1 = isMirrored ? flipX(data.bbox[2]) : flipX(data.bbox[0]);
            const y1 = data.bbox[1] * scaleY;
            const x2 = isMirrored ? flipX(data.bbox[0]) : flipX(data.bbox[2]);
            const y2 = data.bbox[3] * scaleY;
            
            const cL = 18;
            ctx.strokeStyle = color;
            ctx.lineWidth   = 2.5;

            [
                [x1,      y1 + cL, x1, y1,      x1 + cL, y1     ],   // top-left
                [x2 - cL, y1,      x2, y1,      x2,      y1 + cL],   // top-right
                [x1,      y2 - cL, x1, y2,      x1 + cL, y2     ],   // bottom-left
                [x2 - cL, y2,      x2, y2,      x2,      y2 - cL],   // bottom-right
            ].forEach(([ax, ay, bx, by, cx2, cy2]) => {
                ctx.beginPath();
                ctx.moveTo(ax, ay);
                ctx.lineTo(bx, by);
                ctx.lineTo(cx2, cy2);
                ctx.stroke();
            });

            // ── Zone label above bbox ─────────────────────────────────────────
            const zone = data.zone || 'CENTER';
            if (zone !== 'CENTER') {
                const zoneLabels = {
                    LEFT:       '◄ LEFT',
                    RIGHT:      'RIGHT ►',
                    DOWN:       '▼ DOWN',
                    UP:         '▲ UP',
                    DOWN_LEFT:  '▼◄ PHONE',
                    DOWN_RIGHT: '▼► PHONE',
                    UP_LEFT:    '▲◄ ABOVE',
                    UP_RIGHT:   '▲► ABOVE',
                };
                ctx.font      = 'bold 11px "Space Mono", monospace';
                ctx.fillStyle = color;
                ctx.fillText(zoneLabels[zone] || zone, x1, Math.max(14, y1 - 10));
            }

            // ── Head direction arrow ──────────────────────────────────────────
            if (data.head_pose) {
                const cx   = (x1 + x2) / 2;
                const cy   = (y1 + y2) / 2;
                let yaw  = data.head_pose.yaw   || 0;
                const pitch = data.head_pose.pitch || 0;

                if (isMirrored) yaw = -yaw; // Flip yaw direction

                if (Math.abs(yaw) > 4 || Math.abs(pitch) > 4) {
                    const ex = cx + yaw * 1.8 * scaleX;
                    const ey = cy + pitch * 1.8 * scaleY;
                    const aL = 10;
                    const angle = Math.atan2(ey - cy, ex - cx);

                    ctx.strokeStyle = 'rgba(255,184,0,0.85)';
                    ctx.lineWidth   = 2;

                    ctx.beginPath();
                    ctx.moveTo(cx, cy);
                    ctx.lineTo(ex, ey);
                    ctx.stroke();

                    // Arrowhead
                    ctx.beginPath();
                    ctx.moveTo(ex, ey);
                    ctx.lineTo(ex - aL * Math.cos(angle - 0.4), ey - aL * Math.sin(angle - 0.4));
                    ctx.moveTo(ex, ey);
                    ctx.lineTo(ex - aL * Math.cos(angle + 0.4), ey - aL * Math.sin(angle + 0.4));
                    ctx.stroke();
                }
            }
        }

        // ── Iris + nose landmark dots ─────────────────────────────────────────
        if (data.landmarks) {
            const isBlinking  = data.is_blinking === true;
            ctx.fillStyle     = isBlinking ? '#ffb800' : '#ffffff';
            const dotRadius   = isBlinking ? 5 : 3;

            Object.values(data.landmarks).forEach(pt => {
                if (!Array.isArray(pt) || pt.length < 2) return;
                ctx.beginPath();
                ctx.arc(flipX(pt[0]), pt[1] * scaleY, dotRadius, 0, Math.PI * 2);
                ctx.fill();
            });
        }
    }
    // ─────────────────────────────────────────────────────────────────────────

    function updateForensicUI(data) {
        if (!data) return;

        const score     = data.metrics?.focus_score || 0;
        const scoreEl   = $('scoreBig');
        const scoreFill = $('scoreFill');

        if (scoreEl) {
            scoreEl.innerHTML = `${Math.round(score)}<span class="text-cyan-400">%</span>`;
            if (score > 85)      scoreEl.className = "text-5xl font-black text-white drop-shadow-[0_0_15px_rgba(34,211,238,0.4)]";
            else if (score > 60) scoreEl.className = "text-5xl font-black text-yellow-400";
            else                 scoreEl.className = "text-5xl font-black text-red-500";
        }
        if (scoreFill) {
            scoreFill.style.width = `${score}%`;
            scoreFill.className = `h-full transition-all duration-500 ${score > 85 ? 'bg-cyan-400' : score > 60 ? 'bg-yellow-400' : 'bg-red-500'}`;
        }

        const threatEl = $('threatLvl');
        if (threatEl) {
            const status = data.status || 'SAFE';
            threatEl.textContent = status === 'FOCUSED' ? 'MINIMAL' : status;
            threatEl.className = (status === 'SAFE' || status === 'FOCUSED')
                ? "text-xs font-mono font-black text-cyan-400 uppercase tracking-widest"
                : status === 'CAUTION'
                    ? "text-xs font-mono font-black text-yellow-400 uppercase tracking-widest"
                    : "text-xs font-mono font-black text-red-500 uppercase tracking-widest animate-pulse";

            const chip = $('statusChip');
            if (chip) {
                chip.textContent = status === 'FOCUSED' ? 'Safe' : status;
                chip.className = `text-[9px] font-black px-2 py-1 rounded uppercase tracking-widest border ${
                    (status === 'SAFE' || status === 'FOCUSED') ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                    status === 'CAUTION' ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' :
                    'bg-red-500/10 text-red-500 border-red-500/20'
                }`;
            }
        }

        if ($('aiProb'))   $('aiProb').textContent  = `${(data.second_screen_prob || 0).toFixed(1)}%`;
        if ($('driftVal')) $('driftVal').textContent = `±${data.dominance?.toFixed(3) || '0.001'}`;

        if (data.head_pose) {
            const yaw   = data.head_pose.yaw   || 0;
            const pitch = data.head_pose.pitch || 0;

            if ($('yawVal'))   $('yawVal').textContent   = `${Math.round(yaw)}°`;
            if ($('pitchVal')) $('pitchVal').textContent = `${Math.round(pitch)}°`;
            if ($('yawBar'))   $('yawBar').style.width   = `${Math.min(100, Math.max(0, (yaw + 45) * (100 / 90)))}%`;
            if ($('pitchBar')) $('pitchBar').style.width = `${Math.min(100, Math.max(0, (pitch + 45) * (100 / 90)))}%`;
        }

        const probs = {
            'Side':  data.second_screen_prob || 0,
            'Phone': data.phone_prob         || 0,
            'Above': data.screen_above_prob  || 0
        };

        Object.entries(probs).forEach(([key, prob]) => {
            const pct    = Math.round(prob);
            const valEl  = $(`tp${key}`);
            const cardEl = $(`tc${key}`);

            if (valEl) valEl.textContent = `${pct}%`;
            if (cardEl) {
                if (pct > 70)      cardEl.className = "bg-red-500/10 border border-red-500/50 rounded-2xl p-3 text-center transition-all animate-pulse";
                else if (pct > 30) cardEl.className = "bg-yellow-500/10 border border-yellow-500/50 rounded-2xl p-3 text-center transition-all";
                else               cardEl.className = "bg-white/5 border border-white/5 rounded-2xl p-3 text-center transition-all";
            }
        });

        if ($('earBar')) {
            const ear    = data.ear || 0;
            if ($('earVal')) $('earVal').textContent = ear.toFixed(2);
            const earPct = Math.min(100, Math.max(0, (ear - 0.15) * 500));
            $('earBar').style.width = `${earPct}%`;
            $('earBar').className   = ear < 0.22
                ? "h-full bg-yellow-500 transition-all duration-300"
                : "h-full bg-cyan-400 transition-all duration-300";
        }

        if ($('blinkVal')) {
            const isBlinking = data.is_blinking;
            $('blinkVal').textContent = isBlinking ? "BLINK" : "OPEN";
            $('blinkVal').className   = isBlinking
                ? "text-xs font-mono font-bold text-yellow-500 uppercase"
                : "text-xs font-mono font-bold text-green-500 uppercase";
            if ($('blinkPulse')) $('blinkPulse').style.width = isBlinking ? "100%" : "0%";
        }

        if ($('faceMapStatus')) {
            const hasFace = data.status !== 'NO_FACE';
            $('faceMapStatus').textContent = hasFace ? "LOCK ACTIVE" : "CALIBRATION REQUIRED";
            $('faceMapStatus').className   = hasFace
                ? "text-[8px] text-cyan-400 font-mono uppercase tracking-widest"
                : "text-[8px] text-white/10 font-mono uppercase tracking-widest";

            const indicator = $('faceMapIndicator');
            if (indicator) {
                indicator.className = hasFace
                    ? "w-2 h-2 bg-cyan-400 rounded-full shadow-[0_0_10px_#22d3ee]"
                    : "w-2 h-2 bg-white/5 rounded-full";
            }

            const row = $('faceMapRow');
            if (row) row.classList.toggle('active', hasFace);
        }

        // Lexical status is now managed by the dedicated analyzeLexical function

        if ($('domZone')) $('domZone').textContent = data.zone || 'CENTER';
        updateGazeGrid(data.zone);

        if (data.status === 'SUSPICIOUS' || data.status === 'DISTRACTED') {
            addForensicLog(`${data.status}: ${data.reason}`, 'warning');
        }

        // ── NEW: draw canvas overlay on every frame ───────────────────────────
        drawForensicCanvas(data);
    }

    function updateGazeGrid(zone) {
        const grid = $('spatialGrid');
        if (!grid) return;

        const zones = {
            'UP_LEFT': 0, 'UP': 1, 'UP_RIGHT': 2,
            'LEFT': 3,    'CENTER': 4, 'RIGHT': 5,
            'DOWN_LEFT': 6, 'DOWN': 7, 'DOWN_RIGHT': 8
        };
        const idx   = zones[zone] ?? 4;
        const cells = grid.children;

        for (let i = 0; i < cells.length; i++) {
            cells[i].className = i === idx
                ? "bg-cyan-500/40 border border-cyan-400/50 transition-all duration-300"
                : "bg-white/5 border border-white/5";
        }
    }

    function addForensicLog(msg, type = 'system') {
        const log = $('forensic-log');
        if (!log) return;

        const colors = {
            system:  'text-white/40',
            warning: 'text-yellow-400',
            error:   'text-red-400',
            success: 'text-green-400'
        };

        const el = document.createElement('div');
        el.className = `flex gap-3 animate-slide-up ${colors[type] || colors.system}`;
        el.innerHTML = `
            <span class="text-[9px] font-mono text-white/20">${new Date().toLocaleTimeString('en', { hour12: false })}</span>
            <p class="text-[10px] font-mono uppercase tracking-wider">${msg}</p>
        `;
        log.prepend(el);
        if (log.children.length > 20) log.lastElementChild.remove();
    }

});

/**
 * candidate-lobby.js — Candidate Waiting Room Module
 *
 * Professional waiting screen shown to a candidate after they submit
 * a join request and before HR approves them. Handles:
 *   - Verification flow (PENDING → VERIFYING → VERIFIED/FAILED/ERROR)
 *   - Real-time status updates via Supabase
 *   - Nudge alerts from HR
 *   - Approval → auto-rejoin flow
 *
 * Exposes: window.CandidateLobby.show(joinResult, roomId, candidateName, apiBase)
 */

(() => {
    const CandidateLobby = {
        _channel: null,
        _joinFn: null, // callback to re-trigger session join on approval

        /**
         * @param {object}   joinResult  - response from /api/livekit/token
         * @param {string}   roomId
         * @param {string}   candidateName
         * @param {string}   apiBase
         * @param {Function} onApproved  - called when HR approves (usually window.joinSession)
         */
        show(joinResult, roomId, candidateName, apiBase, onApproved) {
            this._joinFn = onApproved;
            const container = document.getElementById('join-lobby');
            if (!container) return;

            // Kick off auto-verification if needed
            if (joinResult.liveness_status === 'PENDING' && joinResult.request_id) {
                if (window.VerificationManager?.init) {
                    window.VerificationManager.init(joinResult.request_id, roomId, candidateName);
                }
            }

            this._render(container, candidateName, joinResult);
            this._subscribeRealtime(roomId, candidateName, apiBase, container, joinResult.request_id);
        },

        // ── Render ────────────────────────────────────────────────────────────
        _render(container, name, result) {
            const step = this._currentStep(result.liveness_status);

            container.innerHTML = `
                <div class="w-full max-w-sm mx-auto flex flex-col items-center px-6 py-10 text-center select-none" id="cl-root">

                    <!-- Identity mark -->
                    <div class="relative mb-8">
                        <div class="absolute -inset-6 rounded-full bg-cyan-500/5 blur-2xl pointer-events-none"></div>
                        <div class="w-20 h-20 rounded-full bg-[#0d1117] border border-white/8 flex items-center justify-center relative">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-white/30">
                                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                                <circle cx="12" cy="7" r="4"/>
                            </svg>
                            <!-- Verified ring -->
                            <div id="cl-ring" class="absolute inset-0 rounded-full border-2 ${
                                result.liveness_status === 'VERIFIED' ? 'border-green-500' : 'border-cyan-500/20'
                            } transition-all duration-500"></div>
                        </div>
                    </div>

                    <!-- Name -->
                    <p class="text-[9px] font-bold text-white/20 uppercase tracking-[0.3em] mb-1">Welcome</p>
                    <h2 class="text-xl font-black text-white mb-8 leading-tight">${this._esc(name)}</h2>

                    <!-- Steps -->
                    <div class="w-full space-y-2 mb-8" id="cl-steps">
                        ${this._stepsHTML(step)}
                    </div>

                    <!-- Status message -->
                    <div id="cl-message" class="text-[10px] font-mono text-white/25 uppercase tracking-widest leading-relaxed max-w-xs">
                        ${this._statusMessage(result.liveness_status)}
                    </div>

                    <!-- Action area -->
                    <div id="cl-action" class="mt-6"></div>
                </div>
            `;
        },

        _currentStep(livenessStatus) {
            if (['PENDING', 'VERIFYING'].includes(livenessStatus)) return 1;
            if (['VERIFIED', 'SKIPPED'].includes(livenessStatus)) return 2;
            return 1;
        },

        _stepsHTML(activeStep) {
            const steps = [
                { n: 1, label: 'Identity Verification', sublabel: 'Gatekeeper AI scan' },
                { n: 2, label: 'Awaiting HR Approval',  sublabel: 'Host will admit you' },
                { n: 3, label: 'Enter Session',          sublabel: 'You\'re in' },
            ];
            return steps.map(s => {
                const done    = s.n < activeStep;
                const active  = s.n === activeStep;
                const pending = s.n > activeStep;
                const dotCls  = done    ? 'bg-cyan-500 border-cyan-500'
                             : active  ? 'bg-transparent border-cyan-400 animate-pulse'
                             :           'bg-transparent border-white/10';
                const lineCls = done ? 'bg-cyan-500/50' : 'bg-white/5';
                const textCls = done || active ? 'text-white' : 'text-white/20';
                return `
                    <div class="flex items-center gap-3">
                        <div class="flex flex-col items-center flex-shrink-0 gap-1">
                            <div class="w-5 h-5 rounded-full border-2 flex items-center justify-center ${dotCls}">
                                ${done ? `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>` : ''}
                                ${active ? `<div class="w-1.5 h-1.5 rounded-full bg-cyan-400"></div>` : ''}
                            </div>
                            ${s.n < 3 ? `<div class="w-px h-4 ${lineCls}"></div>` : ''}
                        </div>
                        <div class="flex-1 text-left pb-4">
                            <p class="text-[10px] font-black uppercase tracking-wider ${textCls}">${s.label}</p>
                            <p class="text-[8px] text-white/20 uppercase tracking-widest">${s.sublabel}</p>
                        </div>
                    </div>
                `;
            }).join('');
        },

        _statusMessage(status) {
            const msgs = {
                PENDING:   'Initializing identity scan — keep your face visible',
                VERIFYING: 'Analyzing video feed — please look at the camera',
                VERIFIED:  'Identity confirmed — waiting for host to admit you',
                SKIPPED:   'Verification bypassed — waiting for host approval',
                FAILED:    'Verification failed — see error below',
                ERROR:     'Technical issue during scan — see details below',
            };
            return msgs[status] || 'Preparing session...';
        },

        // ── Live Updates ─────────────────────────────────────────────────────
        _subscribeRealtime(roomId, name, apiBase, container, requestId) {
            const waitForSupabase = () => {
                if (!window.supabaseClient) { setTimeout(waitForSupabase, 1000); return; }

                this._channel = window.supabaseClient
                    .channel(`cl-${roomId}-${name}`)
                    .on('postgres_changes', {
                        event: 'UPDATE',
                        schema: 'public',
                        table: 'join_requests',
                        filter: `room_id=eq.${roomId}`
                    }, (payload) => {
                        if (payload.new.participant_name !== name) return;
                        this._handleUpdate(payload.new, payload.old, container, name, requestId, roomId, apiBase);
                    })
                    .subscribe();
            };
            waitForSupabase();
        },

        _handleUpdate(data, prev, container, name, requestId, roomId, apiBase) {
            const status = data.liveness_status || 'PENDING';

            // 1. APPROVED — trust backend (backend validates gatekeeper before setting APPROVED)
            if (data.status === 'APPROVED' || data.is_override) {
                this._channel?.unsubscribe();
                this._showApproved(container, name);
                setTimeout(() => {
                    if (typeof this._joinFn === 'function') this._joinFn();
                }, 1800);
                return;
            }

            // 2. REJECTED
            if (data.status === 'REJECTED') {
                this._channel?.unsubscribe();
                this._showRejected(container);
                return;
            }

            // 3. FAILED
            if (status === 'FAILED') {
                this._channel?.unsubscribe();
                this._showFailed(container);
                return;
            }

            // 4. ERROR
            if (status === 'ERROR') {
                this._showError(container, data.error_details, requestId, roomId, name);
                return;
            }

            // 5. VERIFYING / VERIFIED — update steps
            if (['VERIFYING', 'VERIFIED', 'SKIPPED'].includes(status)) {
                const steps = container.querySelector('#cl-steps');
                const msg   = container.querySelector('#cl-message');
                const ring  = container.querySelector('#cl-ring');
                if (steps) steps.innerHTML = this._stepsHTML(this._currentStep(status));
                if (msg)   msg.textContent = this._statusMessage(status);
                if (ring && status === 'VERIFIED') ring.className = 'absolute inset-0 rounded-full border-2 border-green-500 transition-all duration-500';
            }

            // 6. Nudge
            if (prev && data.nudge_count > (prev.nudge_count || 0)) {
                this._showNudge();
            }
        },

        // ── Terminal States ───────────────────────────────────────────────────
        _showApproved(container, name) {
            container.innerHTML = `
                <div class="flex flex-col items-center text-center px-6 py-10">
                    <div class="relative mb-6">
                        <div class="absolute -inset-4 bg-green-500/10 rounded-full blur-xl"></div>
                        <div class="w-16 h-16 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                        </div>
                    </div>
                    <h3 class="text-lg font-black text-white mb-2">Entry Approved</h3>
                    <p class="text-[10px] font-mono text-white/30 uppercase tracking-widest">Connecting you to the session...</p>
                    <div class="mt-6 w-32 h-0.5 bg-white/5 rounded-full overflow-hidden">
                        <div class="h-full bg-green-500 animate-[grow_1.8s_ease-in-out_forwards]" style="width:0%"></div>
                    </div>
                </div>
            `;
        },

        _showRejected(container) {
            container.innerHTML = `
                <div class="flex flex-col items-center text-center px-6 py-10">
                    <div class="w-16 h-16 rounded-full bg-white/5 border border-white/8 flex items-center justify-center mb-6">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-white/30">
                            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </div>
                    <h3 class="text-base font-black text-white/50 mb-2 uppercase tracking-wider">Entry Not Permitted</h3>
                    <p class="text-[9px] font-mono text-white/20 uppercase tracking-widest max-w-xs leading-relaxed">
                        The interviewer has declined this session request. Please contact your recruiter.
                    </p>
                </div>
            `;
        },

        _showFailed(container) {
            container.innerHTML = `
                <div class="flex flex-col items-center text-center px-6 py-10">
                    <div class="relative mb-6">
                        <div class="absolute -inset-4 bg-red-500/10 rounded-full blur-xl"></div>
                        <div class="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f87171" stroke-width="2.5">
                                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                                <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                            </svg>
                        </div>
                    </div>
                    <h3 class="text-base font-black text-red-400 mb-2 uppercase tracking-wider">Verification Failed</h3>
                    <p class="text-[9px] font-mono text-white/30 uppercase tracking-widest max-w-xs leading-relaxed mb-6">
                        Identity verification could not be completed for this session.
                    </p>
                    <button onclick="location.reload()" class="px-6 py-2.5 bg-white/8 hover:bg-white/12 border border-white/8 rounded-xl text-[9px] font-black text-white/50 uppercase tracking-widest transition-all">
                        Try Again
                    </button>
                </div>
            `;
        },

        _showError(container, code, requestId, roomId, name) {
            const msgs = {
                NO_FACE_DETECTED: 'Face not detected — ensure your face is clearly visible and well-lit.',
                POOR_LIGHTING:    'Lighting too low — move to a brighter environment.',
                SYSTEM_OFFLINE:   'Verification server is busy — please wait a moment.',
            };
            const msg = msgs[code] || 'Technical error during scan. Please retry.';

            const action = container.querySelector('#cl-action');
            const message = container.querySelector('#cl-message');
            if (message) {
                message.className = 'text-[10px] font-mono text-amber-400/70 uppercase tracking-widest leading-relaxed max-w-xs';
                message.textContent = msg;
            }
            if (action) {
                action.innerHTML = `
                    <button id="cl-retry" class="px-6 py-2.5 bg-white/8 hover:bg-white/12 border border-white/8 rounded-xl text-[9px] font-black text-white/60 uppercase tracking-widest transition-all">
                        Retry Scan
                    </button>
                `;
                action.querySelector('#cl-retry').onclick = () => {
                    if (window.VerificationManager?.init) {
                        window.VerificationManager.init(requestId, roomId, name);
                        if (message) {
                            message.className = 'text-[10px] font-mono text-white/25 uppercase tracking-widest leading-relaxed max-w-xs';
                            message.textContent = this._statusMessage('VERIFYING');
                        }
                    }
                };
            }
        },

        _showNudge() {
            // Remove any existing nudge
            document.getElementById('cl-nudge')?.remove();

            const el = document.createElement('div');
            el.id = 'cl-nudge';
            el.className = 'fixed inset-x-0 top-24 flex justify-center z-[10000] pointer-events-none';
            el.innerHTML = `
                <div class="flex items-center gap-3 px-5 py-3 bg-amber-500/90 backdrop-blur-xl rounded-2xl shadow-2xl shadow-amber-500/20 border border-amber-400/30 pointer-events-auto"
                     style="animation: nudgePop 0.4s cubic-bezier(0.16,1,0.3,1)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2.5" class="flex-shrink-0">
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                    </svg>
                    <div>
                        <p class="text-[10px] font-black uppercase text-black tracking-wider">Interviewer is waiting</p>
                        <p class="text-[8px] font-bold text-black/60 uppercase">Please complete identity verification</p>
                    </div>
                </div>
            `;
            document.body.appendChild(el);

            try { new Audio('/assets/sounds/nudge.mp3').play(); } catch (e) {}

            setTimeout(() => {
                el.style.animation = 'nudgePop 0.3s cubic-bezier(0.4,0,1,1) reverse forwards';
                setTimeout(() => el.remove(), 300);
            }, 6000);
        },

        // ── Helpers ───────────────────────────────────────────────────────────
        _esc(str) {
            return String(str).replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
    };

    // Inject nudge animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes nudgePop {
            from { transform: translateY(-20px) scale(0.9); opacity: 0; }
            to   { transform: translateY(0) scale(1);       opacity: 1; }
        }
        @keyframes grow {
            from { width: 0%; }
            to   { width: 100%; }
        }
    `;
    document.head.appendChild(style);

    window.CandidateLobby = CandidateLobby;
})();

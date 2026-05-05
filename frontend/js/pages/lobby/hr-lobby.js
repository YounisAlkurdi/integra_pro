/**
 * hr-lobby.js — HR Admission Control Module
 *
 * Handles all HR-side lobby logic:
 *   - Gatekeeper AI toggle (rendered inside session header)
 *   - Lobby card creation / update / removal
 *   - Realtime Supabase subscription for join_requests
 *
 * Exposes: window.HRLobby.init(roomId, apiBase)
 */

(() => {
    const HRLobby = {
        roomId: null,
        apiBase: null,
        settings: { deepfake_required: true },
        _channel: null,

        // ── Public Entry Point ─────────────────────────────────────────────────
        async init(roomId, apiBase) {
            this.roomId  = roomId;
            this.apiBase = apiBase;
            this._injectGatekeeperChip();
            await this._loadInitialSettings();
            await this._loadExistingRequests();
            this._subscribeRealtime();
        },

        // ── Header Chip (Gatekeeper Toggle) ──────────────────────────────────
        _injectGatekeeperChip() {
            const header = document.querySelector('header');
            if (!header) return;
            if (document.getElementById('gk-chip')) return;

            const chip = document.createElement('div');
            chip.id = 'gk-chip';
            chip.className = 'flex items-center gap-3 px-4 py-2 bg-white/5 border border-white/8 rounded-xl cursor-pointer select-none transition-all';
            chip.innerHTML = `
                <div id="gk-dot" class="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#22d3ee]"></div>
                <span class="text-[9px] font-black uppercase tracking-[0.2em] text-white/60 whitespace-nowrap">Gatekeeper</span>
                <span id="gk-label" class="text-[9px] font-black uppercase text-cyan-400">ON</span>
                <label class="relative inline-flex items-center cursor-pointer ml-1">
                    <input type="checkbox" id="gk-toggle" class="sr-only peer" checked>
                    <div class="w-8 h-4 bg-white/10 rounded-full peer peer-checked:after:translate-x-4 peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-cyan-500"></div>
                </label>
            `;

            // Insert before the last flex-child in header (copy invite button area)
            const headerRight = header.querySelector('.flex.items-center.gap-4, .flex.items-center.gap-6');
            if (headerRight) {
                headerRight.insertBefore(chip, headerRight.firstChild);
            } else {
                header.appendChild(chip);
            }

            document.getElementById('gk-toggle').addEventListener('change', (e) => {
                this._onToggleChange(e.target.checked);
            });
        },

        async _loadInitialSettings() {
            try {
                const res = await fetch(`${this.apiBase}/api/livekit/toggle-deepfake?room_id=${this.roomId}`);
                if (!res.ok) return;
                const data = await res.json();
                this.settings.deepfake_required = data.deepfake_required;
                this._syncChipUI(data.deepfake_required);
                const toggle = document.getElementById('gk-toggle');
                if (toggle) toggle.checked = data.deepfake_required;
            } catch (e) { /* no-op — default to true */ }
        },

        _syncChipUI(isActive) {
            const dot   = document.getElementById('gk-dot');
            const label = document.getElementById('gk-label');
            const chip  = document.getElementById('gk-chip');
            if (!dot || !label || !chip) return;

            if (isActive) {
                dot.className   = 'w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#22d3ee]';
                label.textContent = 'ON';
                label.className = 'text-[9px] font-black uppercase text-cyan-400';
                chip.classList.remove('border-amber-500/30');
                chip.classList.add('border-white/8');
            } else {
                dot.className   = 'w-1.5 h-1.5 rounded-full bg-amber-400';
                label.textContent = 'OFF';
                label.className = 'text-[9px] font-black uppercase text-amber-400';
                chip.classList.remove('border-white/8');
                chip.classList.add('border-amber-500/30');
            }
        },

        async _onToggleChange(isActive) {
            this.settings.deepfake_required = isActive;
            this._syncChipUI(isActive);

            // Immediately update all existing lobby card buttons
            document.querySelectorAll('[id^="lc-"]').forEach(card => {
                const status = card.dataset.livenessStatus || 'PENDING';
                this._refreshApproveButton(card, status);
            });

            if (typeof window.showToast === 'function') {
                window.showToast(
                    `Gatekeeper AI ${isActive ? 'Enabled — identity verification required' : 'Bypassed — manual review mode'}`,
                    isActive ? 'info' : 'warning'
                );
            }

            try {
                await fetch(`${this.apiBase}/api/livekit/toggle-deepfake`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ room_id: this.roomId, required: isActive })
                });
            } catch (e) { console.error('[HRLobby] Toggle sync failed:', e); }
        },

        // ── Lobby Container ───────────────────────────────────────────────────
        _getOrCreateContainer() {
            let el = document.getElementById('hr-lobby-notifs');
            if (!el) {
                el = document.createElement('div');
                el.id = 'hr-lobby-notifs';
                el.className = 'fixed bottom-6 right-6 w-80 flex flex-col-reverse gap-3 z-[9999]';
                document.body.appendChild(el);
            }
            return el;
        },

        // ── Lobby Card ────────────────────────────────────────────────────────
        _renderCard(req) {
            if (document.getElementById(`lc-${req.id}`)) return;

            const container = this._getOrCreateContainer();
            const status    = req.liveness_status || 'PENDING';
            const isBlocked = this.settings.deepfake_required && !['VERIFIED', 'SKIPPED'].includes(status);

            // Initials from name
            const initials = (req.participant_name || '?')
                .split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();

            const card = document.createElement('div');
            card.id = `lc-${req.id}`;
            card.dataset.livenessStatus = status;
            card.className = 'bg-[#090d14] border border-white/8 rounded-2xl overflow-hidden shadow-2xl shadow-black/60 backdrop-blur-sm';
            card.style.animation = 'lcSlideIn 0.35s cubic-bezier(0.16,1,0.3,1)';

            card.innerHTML = `
                <!-- Top accent bar -->
                <div class="lc-status-bar h-[2px] ${this._statusBarClass(status)} transition-colors duration-500"></div>

                <div class="p-5">
                    <!-- Row 1: Avatar + Name + Timer -->
                    <div class="flex items-start gap-3.5 mb-4">

                        <!-- Avatar with status ring -->
                        <div class="relative flex-shrink-0">
                            <div class="w-11 h-11 rounded-xl bg-white/5 border border-white/8 flex items-center justify-center">
                                <span class="text-[13px] font-black text-cyan-300 drop-shadow-[0_0_8px_rgba(34,211,238,0.6)] tracking-tight">${initials}</span>
                            </div>
                            <div class="lc-av-ring absolute -inset-[3px] rounded-[14px] border-2 ${this._ringClass(status)} transition-colors duration-500 pointer-events-none"></div>
                        </div>

                        <!-- Name block -->
                        <div class="flex-1 min-w-0 pt-0.5">
                            <p class="text-[8px] font-bold text-white/25 uppercase tracking-[0.2em] mb-0.5">Requesting to Join</p>
                            <p class="text-[14px] font-black text-white leading-tight truncate">${this._esc(req.participant_name)}</p>
                        </div>

                        <!-- Timer -->
                        <span class="lc-timer text-[10px] font-mono text-white/20 tabular-nums flex-shrink-0 pt-1">00:00</span>
                    </div>

                    <!-- Gatekeeper status block -->
                    <div class="lc-gk-block flex items-center gap-2.5 px-3 py-2 rounded-xl bg-white/[0.03] border border-white/5 mb-4">
                        <div class="lc-gk-icon w-6 h-6 rounded-lg flex items-center justify-center ${this._gkIconBg(status)}">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="${this._gkIconColor(status)}"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                        </div>
                        <div class="flex-1 min-w-0">
                            <p class="text-[7px] font-bold text-white/20 uppercase tracking-widest">Gatekeeper AI</p>
                            <p class="lc-badge text-[10px] font-black leading-none ${this._badgeClass(status)}">${this._badgeText(status)}</p>
                        </div>
                        ${status === 'VERIFYING' ? '<div class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping flex-shrink-0"></div>' : ''}
                    </div>

                    <!-- Secondary: Nudge + Override -->
                    <div class="flex gap-2 mb-2">
                        <button class="lc-nudge flex-1 flex items-center justify-center gap-2 py-2 rounded-xl border border-white/6 hover:border-amber-500/20 bg-white/[0.02] hover:bg-amber-500/5 transition-all group">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-white/20 group-hover:text-amber-400 transition-colors"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
                            <span class="text-[8px] font-bold text-white/20 group-hover:text-amber-400 uppercase tracking-wider transition-colors">Nudge</span>
                        </button>
                        <button class="lc-veto flex-1 flex items-center justify-center gap-2 py-2 rounded-xl border border-white/6 hover:border-red-500/20 bg-white/[0.02] hover:bg-red-500/5 transition-all group ${isBlocked ? '' : 'hidden'}">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-white/20 group-hover:text-red-400/80 transition-colors"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                            <span class="text-[8px] font-bold text-white/20 group-hover:text-red-400/80 uppercase tracking-wider transition-colors">Override</span>
                        </button>
                    </div>

                    <!-- Primary actions -->
                    <div class="flex gap-2">
                        <!-- Reject: compact icon button -->
                        <button class="lc-reject w-10 h-10 bg-white/5 hover:bg-red-500/10 border border-white/6 hover:border-red-500/25 rounded-xl flex items-center justify-center transition-all duration-150 flex-shrink-0 group" title="Reject">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-white/25 group-hover:text-red-400 transition-colors"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                        </button>

                        <!-- Approve: full CTA -->
                        <button class="lc-approve flex-1 h-10 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all duration-150 border flex items-center justify-center gap-1.5
                            ${isBlocked
                                ? 'bg-white/3 text-white/20 border-white/5 cursor-not-allowed'
                                : 'bg-cyan-500 hover:bg-cyan-400 text-white border-transparent shadow-lg shadow-cyan-500/20 hover:shadow-cyan-400/30'}" 
                            ${isBlocked ? 'disabled' : ''}>
                            ${isBlocked
                                ? `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg> Verification Required`
                                : `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Admit to Session`
                            }
                        </button>
                    </div>
                </div>
            `;

            container.prepend(card);
            this._startTimer(card, req.created_at);
            this._bindActions(card, req);
        },



        _updateCard(req) {
            const card = document.getElementById(`lc-${req.id}`);
            if (!card) return;

            const status = req.liveness_status || 'PENDING';
            card.dataset.livenessStatus = status;

            // Status bar color
            const bar = card.querySelector('.lc-status-bar');
            if (bar) bar.className = `lc-status-bar h-[2px] ${this._statusBarClass(status)} transition-colors duration-500`;

            // Avatar ring
            const ring = card.querySelector('.lc-av-ring');
            if (ring) ring.className = `lc-av-ring absolute -inset-[3px] rounded-[14px] border-2 ${this._ringClass(status)} transition-colors duration-500 pointer-events-none`;

            // Gatekeeper block
            const badge = card.querySelector('.lc-badge');
            if (badge) {
                badge.className = `lc-badge text-[10px] font-black leading-none ${this._badgeClass(status)}`;
                badge.textContent = this._badgeText(status);
            }
            const gkIcon = card.querySelector('.lc-gk-icon');
            if (gkIcon) {
                gkIcon.className = `lc-gk-icon w-6 h-6 rounded-lg flex items-center justify-center ${this._gkIconBg(status)}`;
                const svg = gkIcon.querySelector('svg');
                if (svg) svg.className = this._gkIconColor(status);
            }

            // Approve + veto visibility
            this._refreshApproveButton(card, status);
            const veto = card.querySelector('.lc-veto');
            if (veto) {
                const blocked = this.settings.deepfake_required && !['VERIFIED', 'SKIPPED'].includes(status);
                veto.classList.toggle('hidden', !blocked);
            }
        },

        _removeCard(id) {
            const card = document.getElementById(`lc-${id}`);
            if (!card) return;
            card.style.animation = 'lcSlideOut 0.25s cubic-bezier(0.4,0,1,1) forwards';
            setTimeout(() => card.remove(), 250);
        },

        _refreshApproveButton(card, status) {
            const btn = card.querySelector('.lc-approve');
            if (!btn) return;
            const isBlocked = this.settings.deepfake_required && !['VERIFIED', 'SKIPPED'].includes(status);
            btn.disabled = isBlocked;
            if (isBlocked) {
                btn.className = 'lc-approve flex-1 h-10 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all duration-150 border flex items-center justify-center gap-1.5 bg-white/3 text-white/20 border-white/5 cursor-not-allowed';
                btn.innerHTML = `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg> Verification Required`;
            } else {
                btn.className = 'lc-approve flex-1 h-10 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all duration-150 border flex items-center justify-center gap-1.5 bg-cyan-500 hover:bg-cyan-400 text-white border-transparent shadow-lg shadow-cyan-500/20 hover:shadow-cyan-400/30';
                btn.innerHTML = `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Admit to Session`;
            }
        },

        // ── Actions ───────────────────────────────────────────────────────────
        _bindActions(card, req) {
            card.querySelector('.lc-reject').onclick = async () => {
                await this._decide(req.participant_name, 'REJECTED');
                this._removeCard(req.id);
            };

            card.querySelector('.lc-approve').onclick = async (e) => {
                const btn = e.currentTarget;
                const status = card.dataset.livenessStatus;

                if (this.settings.deepfake_required && !['VERIFIED', 'SKIPPED'].includes(status)) {
                    if (typeof window.showToast === 'function')
                        window.showToast('Verification incomplete — use Override to bypass', 'warning');
                    return;
                }

                btn.disabled = true;
                btn.innerHTML = '...';
                const ok = await this._decide(req.participant_name, 'APPROVED');
                if (ok) {
                    this._removeCard(req.id);
                } else {
                    btn.disabled = false;
                    this._refreshApproveButton(card, card.dataset.livenessStatus);
                }
            };

            card.querySelector('.lc-nudge').onclick = async () => {
                try {
                    await fetch(`${this.apiBase}/api/livekit/nudge-candidate`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ request_id: req.id })
                    });
                    if (typeof window.showToast === 'function')
                        window.showToast('Nudge sent to candidate', 'info');
                } catch (e) {}
            };

            card.querySelector('.lc-veto').onclick = async () => {
                const reason = prompt(`Emergency Override for ${req.participant_name}\nReason (required):`);
                if (!reason || !reason.trim()) return;

                const ok = await this._decide(req.participant_name, 'APPROVED', true, reason);
                if (ok) {
                    if (typeof window.showToast === 'function')
                        window.showToast('Override granted', 'success');
                    this._removeCard(req.id);
                }
            };
        },

        async _decide(participantName, decision, isOverride = false, overrideReason = '') {
            try {
                const res = await fetch(`${this.apiBase}/api/livekit/decide-request`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        room_id: this.roomId,
                        participant_name: participantName,
                        decision,
                        is_override: isOverride,
                        override_reason: overrideReason
                    })
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    if (typeof window.showToast === 'function')
                        window.showToast(err.detail || 'Action failed', 'error');
                    return false;
                }
                return true;
            } catch (e) {
                if (typeof window.showToast === 'function')
                    window.showToast('Network error', 'error');
                return false;
            }
        },

        // ── Timer ─────────────────────────────────────────────────────────────
        _startTimer(card, createdAt) {
            const timerEl = card.querySelector('.lc-timer');
            const stallingEl = card.querySelector ? null : null;
            const start = createdAt ? new Date(createdAt).getTime() : Date.now();

            const interval = setInterval(() => {
                if (!document.contains(card)) { clearInterval(interval); return; }
                const elapsed = Math.floor((Date.now() - start) / 1000);
                const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
                const s = String(elapsed % 60).padStart(2, '0');
                if (timerEl) timerEl.textContent = `${m}:${s}`;

                // Progress bar fill (caps at 5 min = 300s)
                const bar = card.querySelector('.lc-status-bar');
                if (bar) {
                    const pct = Math.min((elapsed / 300) * 100, 100);
                    bar.style.width = `${pct}%`;
                }
            }, 1000);
        },

        // ── Realtime ─────────────────────────────────────────────────────────
        async _loadExistingRequests() {
            try {
                const res = await fetch(`${this.apiBase}/api/livekit/pending-requests/${this.roomId}`);
                if (res.ok) {
                    const list = await res.json();
                    list.forEach(r => this._renderCard(r));
                }
            } catch (e) { console.error('[HRLobby] Initial load failed:', e); }
        },

        _subscribeRealtime() {
            const waitForSupabase = () => {
                if (!window.supabaseClient) {
                    setTimeout(waitForSupabase, 1000);
                    return;
                }

                this._channel = window.supabaseClient
                    .channel(`hr-lobby-${this.roomId}`)
                    .on('postgres_changes', {
                        event: '*',
                        schema: 'public',
                        table: 'join_requests',
                        filter: `room_id=eq.${this.roomId}`
                    }, (payload) => {
                        if (payload.eventType === 'INSERT') this._renderCard(payload.new);
                        else if (payload.eventType === 'UPDATE') this._updateCard(payload.new);
                        else if (payload.eventType === 'DELETE' && payload.old?.id) this._removeCard(payload.old.id);
                    })
                    .subscribe();
            };
            waitForSupabase();
        },

        // ── Helpers ───────────────────────────────────────────────────────────
        _ringClass(status) {
            return {
                VERIFIED:  'border-green-500/60',
                FAILED:    'border-red-500/60',
                ERROR:     'border-amber-500/60',
                VERIFYING: 'border-blue-400/60',
                SKIPPED:   'border-cyan-500/40',
            }[status] || 'border-white/8';
        },
        _gkIconBg(status) {
            return {
                VERIFIED:  'bg-green-500/15',
                FAILED:    'bg-red-500/15',
                ERROR:     'bg-amber-500/15',
                VERIFYING: 'bg-blue-400/15',
                SKIPPED:   'bg-cyan-500/10',
            }[status] || 'bg-white/5';
        },
        _gkIconColor(status) {
            return {
                VERIFIED:  'text-green-400',
                FAILED:    'text-red-400',
                ERROR:     'text-amber-400',
                VERIFYING: 'text-blue-400',
                SKIPPED:   'text-cyan-400',
            }[status] || 'text-white/20';
        },
        _statusBarClass(status) {
            return {
                VERIFIED:  'bg-green-500',
                FAILED:    'bg-red-500',
                ERROR:     'bg-amber-500',
                VERIFYING: 'bg-blue-400 animate-pulse',
                SKIPPED:   'bg-cyan-500',
            }[status] || 'bg-white/10';
        },
        _badgeClass(status) {
            return {
                VERIFIED:  'text-green-400',
                FAILED:    'text-red-400',
                ERROR:     'text-amber-400',
                VERIFYING: 'text-blue-400',
                SKIPPED:   'text-cyan-400',
            }[status] || 'text-white/25';
        },
        _badgeText(status) {
            return {
                VERIFIED:  'Identity Confirmed',
                FAILED:    'Fraud Detected',
                ERROR:     'Analysis Error',
                VERIFYING: 'Scanning...',
                SKIPPED:   'Protection Off',
            }[status] || 'Awaiting Scan';
        },
        _esc(str) {
            return String(str).replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
    };

    // Inject animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes lcSlideIn {
            from { transform: translateX(110%) scale(0.95); opacity: 0; }
            to   { transform: translateX(0) scale(1);      opacity: 1; }
        }
        @keyframes lcSlideOut {
            from { transform: translateX(0) scale(1);      opacity: 1; max-height: 200px; }
            to   { transform: translateX(110%) scale(0.9); opacity: 0; max-height: 0;     }
        }
    `;
    document.head.appendChild(style);

    window.HRLobby = HRLobby;
})();

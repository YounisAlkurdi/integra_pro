/**
 * Integra Command Console - Core Engine
 * Manages interview streams, node initialization, and system telemetry.
 */

import { supabase } from '../core/supabase-client.js';

document.addEventListener("DOMContentLoaded", async () => {
    if (window.lucide) lucide.createIcons();
    const cursor = document.getElementById('cursor');

    // --- Sidebar Active State Management ---
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            if (link.getAttribute('href') === '#') e.preventDefault();
            sidebarLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });

    // System State
    let createdInterview = null;
    let userSubscription = null;

    // --- 0. Security Protocol (URL Cleaning) ---
    const urlParams = new URLSearchParams(window.location.search);
    if (window.location.hash || urlParams.has('code') || urlParams.has('access_token')) {
        setTimeout(() => {
            const cleanUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
            window.history.replaceState({}, document.title, cleanUrl);
            showToast("Neural link established. Evidence purged.", "system");
        }, 500);
    }

    // --- 0.1 Fetch User Data for Sidebar ---
    try {
        const { data: { user } } = await supabase.auth.getUser();
        if (user) {
            const avatar = document.getElementById('user-avatar');
            const userNameEl = document.getElementById('user-name-display');
            const userIdEl = document.getElementById('user-id-display');

            // 1. Show Name
            if (userNameEl) {
                userNameEl.textContent = user.user_metadata?.full_name || user.email.split('@')[0];
            }

            // 2. Show ID (Optional - for debugging or profile)
            if (userIdEl) {
                userIdEl.textContent = `ID: ${user.id.substring(0, 8)}...`;
            }

            // 3. Set Profile Picture
            if (avatar) {
                const initials = user.user_metadata?.full_name?.split(' ').map(n => n[0]).join('').toUpperCase() || user.email[0].toUpperCase();
                avatar.innerHTML = `<div class="w-full h-full rounded-full bg-obsidian flex items-center justify-center text-[10px] font-bold border border-white/5">\${initials}</div>`;
                
                if (user.user_metadata?.avatar_url) {
                    avatar.innerHTML = `<img src="\${user.user_metadata.avatar_url}" class="w-full h-full rounded-full object-cover">`;
                }
            }
        }
    } catch (e) {
        console.error("Failed to load user information.");
    }

    // --- 1.1 Schedule Toggle ---
    const toggleSchedule = document.getElementById('toggle-schedule');
    const scheduleContainer = document.getElementById('schedule-container');
    const scheduledInput = document.getElementById('scheduledAt');

    const candidateEmail = document.getElementById('candidateEmail');

    if (toggleSchedule) {
        toggleSchedule.addEventListener('change', () => {
            if (toggleSchedule.checked) {
                scheduleContainer.classList.remove('hidden');
                scheduledInput.required = true;
                candidateEmail.required = true;
            } else {
                scheduleContainer.classList.add('hidden');
                scheduledInput.required = false;
                candidateEmail.required = false;
                scheduledInput.value = '';
            }
        });
    }


    // --- 2. Interactive Cursor ---
    if (cursor) {
        document.addEventListener('mousemove', (e) => {
            cursor.style.left = e.clientX + 'px';
            cursor.style.top = e.clientY + 'px';
        });

        document.body.addEventListener('mouseover', (e) => {
            if (['BUTTON', 'A', 'INPUT', 'SELECT'].includes(e.target.tagName) || e.target.closest('.hover-target')) {
                cursor.classList.add('hovering');
            }
        });

        document.body.addEventListener('mouseout', (e) => {
            cursor.classList.remove('hovering');
        });
    }

    // --- 3. Backend Communication Engine ---
    let systemState = {
        profile: null,
        stats: null,
        nodes: [],
        lastSync: 0
    };

    async function getAuthHeader() {
        const { data: { session } } = await supabase.auth.getSession();
        return session ? `Bearer \${session.access_token}` : null;
    }

    async function syncSystemState(force = false) {
        const now = Date.now();
        // 5-second neural buffer (caching) to prevent saturation
        if (!force && systemState.lastSync && (now - systemState.lastSync < 5000)) {
            return systemState;
        }

        try {
            const auth = await getAuthHeader();
            const res = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/init'), {
                headers: { 'Authorization': auth }
            });
            
            if (!res.ok) throw new Error("Sync Interrupted");
            const data = await res.json();
            
            systemState = {
                profile: data.profile,
                stats: data.telemetry,
                nodes: data.active_nodes,
                lastSync: now
            };
            
            // Update global userSubscription for legacy compatibility
            userSubscription = data.profile?.subscription;
            
            return systemState;
        } catch (e) {
            console.error("Neural Sync Failure:", e);
            showToast("Neural Link Interrupted. Retrying...", "error");
            return null;
        }
    }

    async function saveNodeToBackend(nodeData) {
        try {
            const auth = await getAuthHeader();
            const res = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/nodes'), {
                method: 'POST',
                headers: { 
                    'Authorization': auth,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(nodeData)
            });
            const result = await res.json();
            // Invalidate cache on creation
            systemState.lastSync = 0;
            return result;
        } catch (e) { return null; }
    }

    async function sendEmailInvitation(nodeData, room_id) {
        try {
            const auth = await getAuthHeader();
            const roomLink = `\${window.location.origin}/frontend/pages/integra-session.html?room=\${room_id}&role=candidate`;
            
            await fetch(window.INTEGRA_SETTINGS.endpoint('/api/send-invitation'), {
                method: 'POST',
                headers: { 
                    'Authorization': auth,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    candidate_name: nodeData.candidate_name,
                    candidate_email: nodeData.candidate_email,
                    scheduled_at: nodeData.scheduled_at,
                    room_link: roomLink
                })
            });
            showToast("Invitation Transmitted Successfully", "success");
        } catch (e) {
            console.error("Transmission Error:", e);
            showToast("Network Error: Invitation Failed", "error");
        }
    }

    // --- 4. UI Rendering Engine ---
    async function loadActiveStreams() {
        const state = await syncSystemState(true);
        if (state && state.nodes) {
            renderInterviews(state.nodes);
        }
    }

    function renderInterviews(nodes) {
        const container = document.getElementById('interviews-list');
        if (!container) return;
        
        // --- Added: Professional Loading/Empty State with Icons ---
        if (!nodes || nodes.length === 0) {
            container.innerHTML = `
                <div class="flex flex-col items-center justify-center py-20 opacity-20 group">
                    <div class="w-20 h-20 rounded-full border border-dashed border-white/20 flex items-center justify-center mb-6 group-hover:border-cyan-400/40 transition-all duration-700">
                        <i data-lucide="inbox" class="w-10 h-10 mb-0"></i>
                    </div>
                    <p class="text-xs font-mono uppercase tracking-[0.4em] italic">No active data streams detected</p>
                    <p class="text-[8px] font-mono uppercase tracking-[0.2em] mt-2 opacity-50">System Status: Monitoring...</p>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            return;
        }

        container.innerHTML = nodes.map(node => {
            const statusIcon = node.status === 'active' ? 'radio' : 'clock';
            const statusColor = node.status === 'active' ? 'text-cyan-400' : 'text-yellow-500';
            const shadowColor = node.status === 'active' ? 'shadow-[0_0_15px_rgba(34,211,238,0.2)]' : 'shadow-[0_0_15px_rgba(234,179,8,0.1)]';
            
            return `
                <div class="p-6 bg-white/[0.01] border border-white/5 rounded-2xl flex items-center justify-between group hover:border-cyan-400/30 transition-all duration-500 reveal active relative overflow-hidden">
                    <div class="noise-bg opacity-[0.03]"></div>
                    <div class="scanline-overlay opacity-0 group-hover:opacity-[0.03] transition-opacity duration-700"></div>
                    
                    <div class="flex items-center gap-6 relative z-10">
                        <div class="w-14 h-14 rounded-xl bg-cyan-400/5 flex items-center justify-center text-cyan-400 border border-cyan-400/10 group-hover:scale-105 group-hover:bg-cyan-400/10 transition-all duration-500 ${shadowColor}">
                            <i data-lucide="user-plus" class="w-7 h-7"></i>
                        </div>
                        <div>
                            <div class="flex items-center gap-3">
                                <h3 class="text-sm font-black text-white/90 group-hover:text-cyan-400 transition-colors uppercase tracking-widest">${node.candidate_name}</h3>
                                <div class="w-1 h-1 bg-white/20 rounded-full"></div>
                                <span class="text-[9px] font-mono text-cyan-400/40 uppercase tracking-[0.2em]">${node.position}</span>
                            </div>
                            <div class="flex items-center gap-3 mt-1">
                                <p class="text-[10px] font-mono text-white/20 uppercase tracking-widest">Node_ID: <span class="text-white/40">${node.room_id.substring(0,8)}...</span></p>
                                <div class="h-2 w-[1px] bg-white/10"></div>
                                <p class="text-[10px] font-mono text-white/20 uppercase tracking-widest">Role: <span class="text-white/40">Candidate</span></p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-4 relative z-10">
                        <div class="hidden md:flex flex-col items-end mr-8">
                            <span class="text-[7px] font-mono text-white/20 uppercase tracking-[0.3em] mb-1">Neural_Status</span>
                            <div class="flex items-center gap-2">
                                <div class="w-1 h-1 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#22d3ee]"></div>
                                <span class="text-[10px] font-black ${statusColor} uppercase tracking-tighter">${node.status}</span>
                            </div>
                        </div>
                        
                        <div class="flex items-center gap-2">
                            <a href="/frontend/pages/integra-session.html?room=${node.room_id}&role=interviewer" class="p-4 bg-cyan-400/5 text-cyan-400 border border-cyan-400/10 rounded-xl hover:bg-cyan-400 hover:text-obsidian transition-all hover-target group/btn" title="Join as Interviewer">
                                <i data-lucide="external-link" class="w-4 h-4 group-hover/btn:scale-110 transition-transform"></i>
                            </a>
                            <button onclick="copyInterviewLink('${node.room_id}')" class="p-4 bg-white/5 rounded-xl border border-white/5 hover:bg-white/10 text-white/40 hover:text-white transition-all hover-target" title="Copy Candidate Link">
                                <i data-lucide="copy" class="w-4 h-4"></i>
                            </button>
                            <button onclick="confirmDeleteNode('${node.room_id}')" class="p-4 bg-red-500/5 text-red-500/40 border border-red-500/10 rounded-xl hover:bg-red-500 hover:text-white transition-all hover-target" title="Purge Node">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();
    }

    // --- 5. Node Creation Protocol ---
    const createForm = document.getElementById('createInterviewForm');
    if (createForm) {
        createForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('btn-create');
            const btnText = document.getElementById('create-btn-text');
            const overlay = document.getElementById('protocol-overlay');
            const protocolStatus = document.getElementById('protocol-status');
            
            const nodeData = {
                candidate_name: document.getElementById('candidateName').value,
                position: document.getElementById('position').value,
                candidate_email: document.getElementById('candidateEmail')?.value || null,
                scheduled_at: document.getElementById('scheduledAt')?.value || new Date().toISOString(),
                questions: ["Self Introduction", "Technical Background", "System Design Experience"] 
            };

                // --- 1. Quota Check ---
                const state = window.INTEGRA_STATE || {};
                const stats = state.stats;
                const sub = state.profile?.subscription;
                
                if (sub && stats && stats.total >= sub.interviews_limit) {
                    showToast("NEURAL QUOTA EXHAUSTED. UPGRADE PROTOCOL.", "error");
                    btn.disabled = false;
                    btnText.textContent = 'UPGRADE REQUIRED';
                    setTimeout(() => { window.location.href = '/frontend/pages/pricing.html'; }, 2000);
                    return;
                }

                btn.disabled = true;
                const originalBtnHtml = btnText.innerHTML;
                btnText.innerHTML = `<span class="neural-active flex items-center gap-4">NEGOTIATING LINK... <i data-lucide="activity" class="w-5 h-5"></i></span>`;
                if (window.lucide) lucide.createIcons();

                const isScheduled = document.getElementById('toggle-schedule')?.checked;
                
                // Show Professional Protocol Overlay
                if (overlay) {
                    overlay.classList.remove('hidden');
                    overlay.classList.add('flex', 'expand-handshake');
                    
                    const logContainer = document.getElementById('protocol-logs');
                    if (logContainer) logContainer.innerHTML = ''; 
                    
                    const logs = [
                        `Initiating entropy harvest for [${nodeData.candidate_name.substring(0,10)}]...`,
                        "Quantum Key Distribution: SYNCING...",
                        "Bypassing Matrix Firewalls: LAYER_4...",
                        "Provisioning Virtual Node: SUCCESS",
                        "Syncing Identity Database...",
                        "Establishing Neural Bridge: ENCRYPTED",
                        "Link Integrity Verified."
                    ];

                    for (let i = 0; i < logs.length; i++) {
                        await new Promise(r => setTimeout(r, 400 + Math.random() * 400));
                        if (logContainer) {
                            const p = document.createElement('p');
                            p.className = "animate-in slide-in-from-bottom-2 duration-300 text-cyan-400/80 terminal-cursor";
                            p.innerHTML = `<span class="text-white/20">[${new Date().toLocaleTimeString()}]</span> > ${logs[i]}`;
                            logContainer.appendChild(p);
                            logContainer.scrollTop = logContainer.scrollHeight;
                        }
                        if (protocolStatus) protocolStatus.textContent = logs[i].split(':')[0];
                    }
                }
                
                const result = await saveNodeToBackend(nodeData);
                
                if (result && result.room_id) {
                    createdInterview = result;

                    if (!isScheduled) {
                        // --- CASE 1: Instant Join ---
                        showToast("Secure Node Initialized — Entering Room...", "success");
                        btnText.innerHTML = `<span class="neural-active flex items-center gap-4">ENTERING ROOM... <i data-lucide="log-in" class="w-5 h-5"></i></span>`;
                        if (window.lucide) lucide.createIcons();
                        
                        await joinAsHR(result.room_id);
                        
                        // Prevent UI reset by returning early
                        return;
                    } else {
                        // --- CASE 2: Scheduled Link ---
                        const resultDiv = document.getElementById('interviewCreatedResult');
                        const linkInput = document.getElementById('interviewLink');
                        const joinNowLink = document.getElementById('join-now-link');
                        
                        if (resultDiv && linkInput) {
                            const link = `${window.location.origin}/frontend/pages/integra-session.html?room=${result.room_id}&role=candidate`;
                            linkInput.value = link;
                            
                            if (joinNowLink) {
                                joinNowLink.href = `/frontend/pages/integra-session.html?room=${result.room_id}&role=hr`;
                            }
                            
                            resultDiv.classList.remove('hidden');
                            resultDiv.classList.add('neural-active');
                            setTimeout(() => resultDiv.classList.remove('neural-active'), 1000);
                        }

                        showToast("Secure Node Initialized", "success");
                        btnText.innerHTML = `<span class="neural-active flex items-center gap-4">LINK ESTABLISHED <i data-lucide="check" class="w-5 h-5"></i></span>`;
                        if (window.lucide) lucide.createIcons();

                        if (nodeData.candidate_email) {
                            await sendEmailInvitation(nodeData, result.room_id);
                        }
                        
                        // createForm.reset(); // Don't fully reset, user might want to see what they just submitted
                        loadActiveStreams();
                    }
                } else {
                    throw new Error("Initialization Failed");
                }

            } catch (err) {
                showToast("Connection Failed: " + err.message, "error");
            } finally {
                // Only run this cleanup if we haven't redirected (Instant Join returns early)
                btn.disabled = false;
                setTimeout(() => {
                    btnText.innerHTML = originalBtnHtml;
                }, 2000); // Keep success text for a moment
                
                if (overlay) {
                    setTimeout(() => {
                        overlay.classList.add('opacity-0');
                        setTimeout(() => {
                            overlay.classList.add('hidden');
                            overlay.classList.remove('flex', 'expand-handshake', 'opacity-0');
                        }, 500);
                    }, 800);
                }
            }
        });
    }

    window.joinAsHR = async (id) => {
        if (!id) return;

        let hrName = 'HR Operator';
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (user) {
                hrName = user.user_metadata?.full_name || user.email?.split('@')[0] || hrName;
            }
        } catch (_) {}

        const params = new URLSearchParams({ room: id, role: 'hr', name: hrName });
        window.location.href = `/frontend/pages/integra-session.html?${params.toString()}`;
    };

    const sendEmailInvitation = async (nodeData, roomId) => {
        try {
            const auth = await getAuthHeader();
            const roomLink = `${window.location.origin}/frontend/pages/integra-session.html?room=${roomId}&role=candidate`;
            
            await fetch(window.INTEGRA_SETTINGS.endpoint('/api/send-invitation'), {
                method: 'POST',
                headers: { 
                    'Authorization': auth,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    candidate_name: nodeData.candidate_name,
                    candidate_email: nodeData.candidate_email,
                    scheduled_at: nodeData.scheduled_at,
                    room_link: roomLink
                })
            });
            showToast("Invitation Transmitted Successfully", "success");
        } catch (e) {
            console.error("Email Transmission Error:", e);
            showToast("Notification Failed: Network Error", "error");
        }
    };

    window.copyInterviewLink = (roomId) => {
        const linkInput = document.getElementById('interviewLink');
        let textToCopy = "";
        
        if (roomId) {
            textToCopy = `${window.location.origin}/frontend/pages/integra-session.html?room=${roomId}&role=candidate`;
        } else if (linkInput) {
            textToCopy = linkInput.value;
        }

        if (textToCopy) {
            navigator.clipboard.writeText(textToCopy).then(() => {
                showToast("Link Copied to Clipboard", "success");
                const copyBtn = document.getElementById('btn-copy');
                if (copyBtn) {
                    const originalText = copyBtn.textContent;
                    copyBtn.textContent = "COPIED!";
                    setTimeout(() => copyBtn.textContent = originalText, 2000);
                }
            });
        }
    };

    window.confirmDeleteNode = (roomId) => {
        const modal = document.getElementById('confirm-modal');
        const confirmBtn = document.getElementById('confirm-proceed');
        const cancelBtn = document.getElementById('confirm-cancel');

        if (!modal) return;

        modal.classList.remove('hidden');
        
        const close = () => modal.classList.add('hidden');
        
        cancelBtn.onclick = close;
        confirmBtn.onclick = async () => {
            try {
                const auth = await getAuthHeader();
                const res = await fetch(window.INTEGRA_SETTINGS.endpoint(`/api/nodes/${roomId}`), {
                    method: 'DELETE',
                    headers: { 'Authorization': auth }
                });
                
                if (res.ok) {
                    showToast("Node Purged Successfully", "system");
                    loadActiveStreams();
                } else {
                    showToast("Purge Protocol Failed", "error");
                }
            } catch (e) {
                showToast("Network Error during Purge", "error");
            } finally {
                close();
            }
        };
    };

    window.refreshInterviews = () => {
        showToast("Synchronizing Streams...", "system");
        loadActiveStreams();
    };

    // --- 9. Security Audit Monitor ---
    async function loadDashboardAuditLogs() {
        try {
            const auth = await getAuthHeader();
            const res = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/system/audit-summary'), {
                headers: { 'Authorization': auth }
            });
            
            if (!res.ok) return;
            const logs = await res.json();
            
            const auditContainer = document.getElementById('dashboard-audit-logs');
            if (!auditContainer) return;

            if (!logs || logs.length === 0) {
                auditContainer.innerHTML = `
                    <div class="flex flex-col items-center justify-center py-10 opacity-20">
                        <i data-lucide="shield-check" class="w-8 h-8 mb-2"></i>
                        <p class="text-[9px] font-mono uppercase tracking-[0.3em]">No critical events detected</p>
                    </div>
                `;
                lucide.createIcons();
                return;
            }

            auditContainer.innerHTML = logs.map(log => {
                const severityColors = {
                    'INFO': 'text-cyan-400',
                    'WARNING': 'text-yellow-500',
                    'CRITICAL': 'text-red-500',
                    'ERROR': 'text-red-400'
                };
                
                const severityIcons = {
                    'INFO': 'info',
                    'WARNING': 'alert-triangle',
                    'CRITICAL': 'alert-octagon',
                    'ERROR': 'x-circle'
                };

                const color = severityColors[log.severity] || 'text-cyan-400';
                const icon = severityIcons[log.severity] || 'shield';
                
                return `
                    <div class="flex items-center justify-between p-4 bg-white/[0.02] border border-white/5 rounded-xl hover:bg-white/[0.04] transition-all group reveal active">
                        <div class="flex items-center gap-4">
                            <div class="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center border border-white/5 group-hover:border-cyan-400/20 transition-all">
                                <i data-lucide="${icon}" class="w-4 h-4 ${color}"></i>
                            </div>
                            <div>
                                <p class="text-[10px] font-bold text-white group-hover:text-cyan-400 transition-colors uppercase tracking-wider">${log.action.replace(/_/g, ' ')}</p>
                                <p class="text-[8px] font-mono text-white/20 uppercase tracking-widest mt-0.5">${formatDate(log.created_at)} • <span class="text-white/40">${log.resource || 'SYSTEM'}</span></p>
                            </div>
                        </div>
                        <div class="text-[8px] font-mono text-white/10 group-hover:text-white/30 transition-all uppercase tracking-[0.2em] hidden sm:block">
                            NODE_IP: ${log.ip || 'INTERNAL'}
                        </div>
                    </div>
                `;
            }).join('');
            
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error("Failed to load audit telemetry:", e);
        }
    }

    // --- 10. Quick Protocol Handlers ---
    const setupProtocolListeners = () => {
        const rebootBtn = document.getElementById('protocol-reboot');
        const pruneBtn = document.getElementById('protocol-prune');
        const lockdownBtn = document.getElementById('protocol-lockdown');

        if (rebootBtn) {
            rebootBtn.addEventListener('click', async () => {
                if (confirm("INITIATE CORE REBOOT? This will temporarily interrupt neural sync.")) {
                    try {
                        const auth = await getAuthHeader();
                        const res = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/system/reboot'), {
                            method: 'POST',
                            headers: { 'Authorization': auth }
                        });
                        const data = await res.json();
                        if (data.status === "SUCCESS") {
                            showToast("REBOOT SEQUENCE INITIATED", "system");
                            setTimeout(() => window.location.reload(), 2000);
                        }
                    } catch (e) { showToast("REBOOT SIGNAL FAILED", "error"); }
                }
            });
        }

        if (pruneBtn) {
            pruneBtn.addEventListener('click', async () => {
                try {
                    showToast("PRUNING STALE ARCHIVES...", "system");
                    const auth = await getAuthHeader();
                    const res = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/system/prune'), {
                        method: 'POST',
                        headers: { 'Authorization': auth }
                    });
                    const data = await res.json();
                    if (data.status === "SUCCESS") {
                        showToast("ARCHIVE PRUNING COMPLETE", "success");
                        loadDashboardAuditLogs();
                    }
                } catch (e) { showToast("PRUNE PROTOCOL FAILED", "error"); }
            });
        }

        if (lockdownBtn) {
            lockdownBtn.addEventListener('click', async () => {
                const action = "TOGGLE EMERGENCY LOCKDOWN";
                if (confirm(`${action}? This will restrict all non-commander access.`)) {
                    try {
                        const auth = await getAuthHeader();
                        const res = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/system/lockdown'), {
                            method: 'POST',
                            headers: { 'Authorization': auth }
                        });
                        const data = await res.json();
                        if (data.status === "SUCCESS") {
                            const msg = data.locked ? "SYSTEM SECURED: LOCKDOWN ACTIVE" : "SYSTEM RESTORED: LOCKDOWN LIFTED";
                            showToast(msg, data.locked ? "error" : "success");
                            
                            const status = document.getElementById('connection-status');
                            if (status) {
                                if (data.locked) {
                                    status.innerHTML = '<div class="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse shadow-[0_0_8px_#ef4444]"></div> LOCKDOWN';
                                    status.classList.add('border-red-500/20', 'text-red-500');
                                    status.classList.remove('border-cyan-400/20', 'text-cyan-400');
                                } else {
                                    status.innerHTML = '<div class="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse shadow-[0_0_8px_#22d3ee]"></div> Active';
                                    status.classList.remove('border-red-500/20', 'text-red-500');
                                    status.classList.add('border-cyan-400/20', 'text-cyan-400');
                                }
                            }
                            loadDashboardAuditLogs();
                        }
                    } catch (e) { showToast("LOCKDOWN SIGNAL FAILED", "error"); }
                }
            });
        }
    };

    function formatDate(dateStr) {
        if (!dateStr) return 'RECENT';
        const date = new Date(dateStr);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    // --- 8. UI Rendering Engine (Updated) ---
    async function updateDashboardUI() {
        const state = await syncSystemState();
        if (!state) return;

        const { stats, profile, nodes } = state;
        
        // Update Stats
        if (stats) {
            if (document.getElementById('stat-total')) document.getElementById('stat-total').textContent = stats.total || 0;
            if (document.getElementById('stat-active')) document.getElementById('stat-active').textContent = stats.active || 0;
            if (document.getElementById('stat-completed')) document.getElementById('stat-completed').textContent = stats.completed || 0;
        }

        // Render nodes
        if (nodes) renderInterviews(nodes);
        
        // Add audit logs load
        loadDashboardAuditLogs();
    }

    // Initialize listeners
    setupProtocolListeners();

    // --- 8. Initial Initialization ---
    await updateDashboardUI();

    // --- REACTIVE NEURAL UPDATES ---
    window.addEventListener('integra-system-event', (e) => {
        const { event } = e.detail;
        console.log(`[Neural Dashboard] Reacting to event: ${event}`);
        
        if (["node-created", "node-deleted", "matrix-update", "security-event"].includes(event)) {
            loadActiveStreams();
            loadDashboardAuditLogs();
        }
    });
});

// --- Toast Notification Protocol ---
window.showToast = function(msg, type = "success") { 
    const container = document.getElementById('toast-container') || createToastContainer(); 
    const toast = document.createElement('div'); 
    
    const colors = {
        success: 'border-cyan-400 text-cyan-400 bg-cyan-400/5',
        error: 'border-red-500 text-red-500 bg-red-400/5',
        system: 'border-white/20 text-white bg-white/5',
        info: 'border-white/40 text-white/80 bg-white/5'
    };

    toast.className = `px-6 py-4 border rounded-xl backdrop-blur-xl animate-in slide-in-from-right-10 flex items-center gap-4 text-[10px] font-mono uppercase tracking-[0.2em] mb-3 pointer-events-auto shadow-2xl ${colors[type] || colors.success}`; 
    toast.innerHTML = `<div class="w-1.5 h-1.5 rounded-full bg-current ${type === 'success' ? 'animate-pulse' : ''}"></div> ${msg}`; 
    
    container.appendChild(toast); 
    
    setTimeout(() => {
        toast.classList.add('animate-out', 'fade-out', 'slide-out-to-right-10');
        setTimeout(() => toast.remove(), 500);
    }, 4000);
} 

function createToastContainer() { 
    const div = document.createElement('div'); 
    div.id = 'toast-container'; 
    div.className = 'fixed bottom-10 right-10 z-[100] flex flex-col gap-3'; 
    document.body.appendChild(div); 
    return div; 
}


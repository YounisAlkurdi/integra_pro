/**
 * Integra Command Console - Core Engine
 * Manages interview streams, node initialization, and system telemetry.
 */

// --- 1. Global Setup ---
// Supabase is already initialized in script.js (referenced in dashboard.html)

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
                avatar.innerHTML = `<div class="w-full h-full rounded-full bg-obsidian flex items-center justify-center text-[10px] font-bold border border-white/5">${initials}</div>`;
                
                if (user.user_metadata?.avatar_url) {
                    avatar.innerHTML = `<img src="${user.user_metadata.avatar_url}" class="w-full h-full rounded-full object-cover">`;
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


    // --- 2. Interactive Cursor ---
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

    // --- 3. Backend Communication Engine ---
    async function getAuthHeader() {
        const { data: { session } } = await supabase.auth.getSession();
        return session ? `Bearer ${session.access_token}` : null;
    }

    async function fetchNodeStats() {
        try {
            const auth = await getAuthHeader();
            const res = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/stats'), {
                headers: { 'Authorization': auth }
            });
            return await res.json();
        } catch (e) { return null; }
    }

    async function fetchNodes() {
        try {
            const auth = await getAuthHeader();
            const res = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/nodes'), {
                headers: { 'Authorization': auth }
            });
            return await res.json();
        } catch (e) { return []; }
    }

    async function fetchSubscription() {
        try {
            const auth = await getAuthHeader();
            const response = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/user-profile'), {
                headers: { 'Authorization': auth }
            });
            
            if (!response.ok) throw new Error("Sync Interrupted");
            const data = await response.json();
            
            // The backend now provides the latest active subscription with all limits enforced
            userSubscription = data.subscription || { interviews_limit: 5, plan_id: 'free', max_duration_mins: 10, max_participants: 2 };
            return userSubscription;
        } catch (e) {
            console.warn("Neural Link: Backend sync failed. Retrying in bypass mode.");
            // Manual check as last resort
            const { data: { user } } = await supabase.auth.getUser();
            const { data } = await supabase.from('subscriptions').select('*').eq('user_id', user.id).order('created_at', { ascending: false }).limit(1);
            
            let sub = data && data[0] ? data[0] : { interviews_limit: 5, plan_id: 'free', max_duration_mins: 10, max_participants: 2 };
            
            // Repair in-memory if needed
            if (sub.plan_id) {
                const templates = {
                    'starter': { interviews_limit: 15, max_duration_mins: 20, max_participants: 4 },
                    'professional': { interviews_limit: 40, max_duration_mins: 60, max_participants: 8 },
                    'enterprise': { interviews_limit: 9999, max_duration_mins: 1440, max_participants: 100 },
                    'nexus': { interviews_limit: 50, max_duration_mins: 60, max_participants: 5 },
                    'free': { interviews_limit: 5, max_duration_mins: 10, max_participants: 2 }
                };
                const tpl = templates[sub.plan_id] || templates['free'];
                
                if (!sub.interviews_limit || sub.interviews_limit === 5) {
                    sub.interviews_limit = tpl.interviews_limit;
                    sub.max_duration_mins = tpl.max_duration_mins;
                    sub.max_participants = tpl.max_participants;
                } else {
                    sub.interviews_limit = sub.interviews_limit || tpl.interviews_limit;
                    sub.max_duration_mins = sub.max_duration_mins || tpl.max_duration_mins;
                    sub.max_participants = sub.max_participants || tpl.max_participants;
                }
            }

            userSubscription = sub;
            return userSubscription;
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
            return await res.json();
        } catch (e) { return null; }
    }

    async function sendEmailInvitation(nodeData, room_id) {
        try {
            const auth = await getAuthHeader();
            const roomLink = `${window.location.origin}/integra-session.html?room=${room_id}&role=candidate`;
            
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
    async function updateStats() {
        const stats = await fetchNodeStats();
        const sub = userSubscription || await fetchSubscription();
        
        if (stats) {
            document.getElementById('stat-total').textContent = `${stats.total}/${sub?.interviews_limit || 5}`;
            document.getElementById('stat-active').textContent = stats.active;
            document.getElementById('stat-completed').textContent = stats.completed;
            
            // Update Node Capacity display
            const capacityEl = document.getElementById('stat-capacity');
            if (capacityEl) {
                const mins = sub?.max_duration_mins || 10;
                const parts = sub?.max_participants || 2;
                capacityEl.textContent = `${mins}m / ${parts}P`;
            }

            // Legacy support for flagged element
            const flaggedEl = document.getElementById('stat-flagged');
            if (flaggedEl) flaggedEl.textContent = stats.threats.toString().padStart(2, '0');
            
            // Highlight limit if reached
            if (sub && stats.total >= sub.interviews_limit) {
                document.getElementById('stat-total').classList.add('text-red-500', 'animate-pulse');
            }
        }
    }

    async function renderInterviews() {
        const list = document.getElementById('interviews-list');
        const sessions = await fetchNodes();

        if (!sessions || sessions.length === 0) {
            list.innerHTML = `
                <div class="flex flex-col items-center justify-center py-20 opacity-20">
                    <i data-lucide="inbox" class="w-12 h-12 mb-4"></i>
                    <p class="text-xs font-mono uppercase tracking-[0.3em]">No streams detected</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        list.innerHTML = sessions.map(s => `
            <div class="group relative bg-white/[0.01] border border-white/5 p-6 rounded-2xl hover:bg-white/[0.03] hover:border-cyan-400/20 transition-all duration-500 overflow-hidden reveal active cursor-pointer">
                <div class="flex justify-between items-center gap-6 relative z-10">
                    <div class="flex items-center gap-4">
                        <div class="w-10 h-10 bg-cyan-400/10 rounded-full flex items-center justify-center text-cyan-400 font-mono text-xs border border-cyan-400/20">
                            ${(s.candidate_name || 'N').charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <h4 class="text-sm font-bold tracking-tight text-white group-hover:text-cyan-400 transition-colors">${s.candidate_name || 'Unknown'}</h4>
                            <div class="flex items-center gap-3 mt-1">
                                <p class="text-[9px] font-mono text-white/30 uppercase tracking-[0.2em]">${s.position || 'N/A'}</p>
                                <span class="text-[8px] text-white/10">•</span>
                                <p class="text-[9px] font-mono text-cyan-400/40 uppercase tracking-[0.2em]">📅 ${formatDate(s.scheduled_at)}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-6">
                        <span class="text-[8px] font-mono text-white/20 uppercase tracking-widest hidden sm:block">ID: ${s.room_id.substring(0, 8)}</span>
                        <div class="flex items-center gap-3">
                            <span class="px-3 py-1 bg-cyan-400/5 border border-cyan-400/20 text-cyan-400 text-[8px] font-bold uppercase rounded-full tracking-[0.2em]">${s.status}</span>
                            <button onclick="copyLink('${s.room_id}')" class="p-2 hover:text-cyan-400 transition-all" title="Copy Candidate Link"><i data-lucide="link" class="w-4 h-4"></i></button>
                            <button onclick="terminateSession('${s.room_id}')" class="p-2 hover:text-red-500 transition-all" title="Terminate Session"><i data-lucide="x" class="w-4 h-4"></i></button>
                            <button onclick="joinAsHR('${s.room_id}')" class="px-4 py-2 bg-white/5 hover:bg-white text-obsidian text-[8px] font-bold uppercase rounded-lg transition-all hover-target"><i data-lucide="play" class="w-3 h-3 inline mr-1"></i> Join</button>
                        </div>
                    </div>
                </div>
                <div class="absolute inset-0 bg-gradient-to-r from-cyan-400/0 via-cyan-400/0 to-cyan-400/0 group-hover:from-cyan-400/5 group-hover:via-transparent transition-all duration-700"></div>
            </div>
        `).join('');
        
        lucide.createIcons();
        init3DTilt();
    }



    // --- 6. Form Submission Protocol ---
    document.getElementById('createInterviewForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btn = document.getElementById('btn-create');
        const text = document.getElementById('create-btn-text');
        
        // --- Security Check: Quota Verification ---
        const stats = await fetchNodeStats();
        const sub = userSubscription || await fetchSubscription();
        
        if (sub && stats && stats.total >= sub.interviews_limit) {
            showToast("NEURAL QUOTA EXHAUSTED. UPGRADE PROTOCOL.", "error");
            btn.disabled = false;
            text.textContent = 'UPGRADE REQUIRED';
            
            // Redirect to pricing after delay
            setTimeout(() => { window.location.href = 'pricing.html'; }, 2000);
            return;
        }

        btn.disabled = true;
        text.textContent = 'ESTABLISHING LINK...';

        const nodeData = {
            candidate_name: document.getElementById('candidateName').value,
            candidate_email: document.getElementById('candidateEmail').value,
            position: document.getElementById('position').value,
            questions: [], 
            scheduled_at: toggleSchedule.checked ? scheduledInput.value : new Date().toISOString(),
            // Inject subscription limits into the node record
            max_duration_mins: sub?.max_duration_mins || 10,
            max_participants: sub?.max_participants || 2
        };

        const result = await saveNodeToBackend(nodeData);

        if (result) {
            createdInterview = result;

            if (!toggleSchedule.checked) {
                // ── Instant session: go directly to the room ──
                showToast("Secure Node Initialized — Entering Room...", "success");
                await window.joinAsHR(result.room_id);
            } else {
                // ── Scheduled: show shareable link panel ──
                document.getElementById('interviewLink').value = `${window.location.origin}/integra-session.html?room=${result.room_id}&role=candidate`;
                document.getElementById('interviewCreatedResult').classList.remove('hidden');

                btn.disabled = false;
                text.textContent = 'LINK ESTABLISHED';

                showToast("Secure Node Initialized", "success");
                
                // --- Automatic Invitation Dispatch ---
                if (nodeData.candidate_email) {
                    await sendEmailInvitation(nodeData, result.room_id);
                }

                renderInterviews();
                updateStats();
            }
        } else {
            showToast("Connection Interrupted: Node Failed", "error");
            btn.disabled = false;
            text.textContent = 'RETRY INITIALIZATION';
        }
    });


    // --- 7. Utility Functions ---
    function formatDate(dateStr) {
        if (!dateStr) return 'TBD';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: '2-digit', day: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    window.copyInterviewLink = () => {
        const input = document.getElementById('interviewLink');
        input.select();
        document.execCommand('copy');
        document.getElementById('btn-copy').textContent = 'COPIED';
        showToast("Link Securely Copied", "info");
        setTimeout(() => document.getElementById('btn-copy').textContent = 'COPY', 2000);
    };

    window.copyLink = (id) => {
        const link = `${window.location.origin}/interview.html?room=${id}&role=candidate`;
        navigator.clipboard.writeText(link).then(() => {
            showToast("Session Hash Copied", "info");
        });
    };

    window.joinAsHR = async (id) => {
        const rid = id || (createdInterview ? createdInterview.room_id : '');
        if (!rid) return;

        // Fetch current user name to pre-fill session
        let hrName = 'HR Operator';
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (user) {
                hrName = user.user_metadata?.full_name || user.email?.split('@')[0] || hrName;
            }
        } catch (_) {}
        
        // منع التضارب: إضافة رقم عشوائي صغير للاسم حتى لو شخصين دخلوا بنفس الحساب ما يطردوا بعض
        const randomSuffix = Math.floor(1000 + Math.random() * 9000);
        hrName = `${hrName} #${randomSuffix}`;

        const params = new URLSearchParams({ room: rid, role: 'hr', name: hrName });
        window.location.href = `integra-session.html?${params.toString()}`;
    };

    window.refreshInterviews = async () => {
        showToast("Synchronizing Neural Buffer...", "system");
        await renderInterviews();
        await updateStats();
    };

    window.terminateSession = async (rid) => {
        const modal = document.getElementById('confirm-modal');
        const btnConfirm = document.getElementById('confirm-proceed');
        const btnCancel = document.getElementById('confirm-cancel');

        // Show Modal
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        lucide.createIcons();

        const userChoice = await new Promise((resolve) => {
            const handleConfirm = () => {
                modal.classList.add('hidden');
                modal.classList.remove('flex');
                cleanup();
                resolve(true);
            };
            const handleCancel = () => {
                modal.classList.add('hidden');
                modal.classList.remove('flex');
                cleanup();
                resolve(false);
            };
            const cleanup = () => {
                btnConfirm.removeEventListener('click', handleConfirm);
                btnCancel.removeEventListener('click', handleCancel);
            };

            btnConfirm.addEventListener('click', handleConfirm);
            btnCancel.addEventListener('click', handleCancel);
        });

        if (!userChoice) return;

        try {
            showToast("EXECUTING PURGE PROTOCOL...", "system");
            const auth = await getAuthHeader();
            
            // 1. Force-terminate LiveKit Room (Kicks everyone out)
            const lkRes = await fetch(window.INTEGRA_SETTINGS.endpoint(`/api/livekit/room/${rid}`), {
                method: 'DELETE',
                headers: { 'Authorization': auth }
            });
            
            if (!lkRes.ok) {
                console.warn("LiveKit Room might already be inactive. Proceeding with DB cleanup.");
            }

            // 2. Remove from Local Registry (DB)
            const nodeRes = await fetch(window.INTEGRA_SETTINGS.endpoint(`/api/nodes/${rid}`), {
                method: 'DELETE',
                headers: { 'Authorization': auth }
            });

            if (nodeRes.ok || lkRes.ok) {
                showToast("SESSION TERMINATED & PURGED", "success");
                await renderInterviews();
                await updateStats();
            } else {
                showToast("Purge Signal Interrupted", "error");
            }
        } catch (e) {
            console.error("Critical Failure in Termination Module:", e);
            showToast("Critical Failure in Termination Module", "error");
        }
    };

    function init3DTilt() {
        const cards = document.querySelectorAll('#interviews-list .group');
        cards.forEach(card => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                const rotateX = (y - centerY) / 25; 
                const rotateY = (centerX - x) / 25;
                card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
            });
            card.addEventListener('mouseleave', () => {
                card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
            });
            card.style.transition = 'transform 0.1s ease-out';
        });
    }

    // --- 8. Initial Initialization ---
    await renderInterviews();
    await updateStats();
});

// --- Toast Notification Protocol ---
function showToast(msg, type = "success") { 
    const container = document.getElementById('toast-container') || createToastContainer(); 
    const toast = document.createElement('div'); 
    
    // Aesthetic Palette
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

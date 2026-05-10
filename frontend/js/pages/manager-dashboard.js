/**
 * Integra Executive Dashboard Logic
 * Managed by Antigravity AI
 */

import { supabase } from '../core/supabase-client.js';

const API_BASE = window.INTEGRA_SETTINGS?.backend_url || 'http://127.0.0.1:8000';
const endpoint = (path) => `${API_BASE}${path}`;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initial State
    let selectedRecruiterId = null;
    let currentRating = 0;
    const recruiters = [];

    // Get Auth Session
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) return; // Handled by inline script in HTML

    const authHeaders = {
        'Authorization': `Bearer ${session.access_token}`,
        'Content-Type': 'application/json'
    };

    // --- Heartbeat (Activity Tracking) ---
    async function startHeartbeat() {
        const updateActivity = async () => {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) return;
            await supabase.from('profiles').update({ updated_at: new Date().toISOString() }).eq('id', user.id);
        };
        updateActivity();
        setInterval(updateActivity, 60000);
    }
    startHeartbeat();

    // 2. DOM Elements
    const recruiterListBody = document.getElementById('recruiter-list-body');
    const orgNameDisplay = document.getElementById('org-name-display');
    const teamEfficiencyStat = document.getElementById('team-efficiency-stat');
    const teamSizeStat = document.getElementById('team-size-stat');
    const securityAlertsContainer = document.getElementById('security-alerts-container');
    
    const evaluationForm = document.getElementById('evaluation-form');
    const selectedRecruiterName = document.getElementById('selected-recruiter-name');
    const starRatingContainer = document.getElementById('star-rating-container');
    const submitEvalBtn = document.getElementById('submit-eval-btn');
    const evalFeedback = document.getElementById('eval-feedback');

    // 3. Initialize Stars
    const starTemplate = document.getElementById('star-template');
    if (starTemplate && starRatingContainer) {
        for (let i = 1; i <= 5; i++) {
            const starClone = starTemplate.content.cloneNode(true);
            const btn = starClone.querySelector('button');
            btn.dataset.rating = i;
            btn.addEventListener('click', () => setRating(i));
            starRatingContainer.appendChild(starClone);
        }
        if (window.lucide) lucide.createIcons();
    }

    // 4. Fetch Data Functions
    async function fetchData() {
        try {
            // Fetch stats
            const statsRes = await fetch(`${API_BASE}/api/manager/stats`, { headers: authHeaders });
            if (!statsRes.ok) throw new Error('Failed to fetch stats');
            const stats = await statsRes.json();
            
            // Update stats UI
            if (teamEfficiencyStat) teamEfficiencyStat.textContent = `${stats.avg_candidate_score || 0}%`;
            if (teamSizeStat) teamSizeStat.textContent = stats.active_recruiters || 0;
            if (orgNameDisplay) orgNameDisplay.textContent = `Organization: ${stats.org_name || 'Enterprise'}`;
            
            // Populate Settings tab org name
            const settingsOrgName = document.getElementById('settings-org-name');
            if (settingsOrgName) settingsOrgName.value = stats.org_name || '';

            // Fetch recruiters
            const recruiterRes = await fetch(`${API_BASE}/api/manager/recruiters`, { headers: authHeaders });
            if (!recruiterRes.ok) throw new Error('Failed to fetch recruiters');
            const recruiterData = await recruiterRes.json();
            
            renderRecruiterList(recruiterData);
            renderTeamAccessList(recruiterData);
            updateChart(recruiterData);

            // Fetch live alerts and billing in parallel
            await Promise.all([
                renderSecurityAlerts(),
                fetchBillingData()
            ]);

        } catch (error) {
            console.error('Failed to sync executive data:', error);
            if (recruiterListBody) {
                recruiterListBody.innerHTML = `<tr><td colspan="4" class="py-8 text-center text-red-400/80 text-xs font-mono uppercase tracking-widest">Error fetching data</td></tr>`;
            }
        }
    }

    function renderRecruiterList(data) {
        if (!recruiterListBody) return;
        recruiterListBody.innerHTML = '';
        
        if (data.length === 0) {
            recruiterListBody.innerHTML = `<tr><td colspan="4" class="py-8 text-center text-white/20 italic">No recruiters found in your organization.</td></tr>`;
            return;
        }

        data.forEach(r => {
            const tr = document.createElement('tr');
            tr.className = 'group hover:bg-white/5 transition-colors cursor-pointer';
            tr.innerHTML = `
                <td class="py-4">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center font-bold text-[10px] text-cyan-400 border border-white/10 group-hover:border-cyan-400/50 transition-all">
                            ${r.full_name ? r.full_name.substring(0, 2).toUpperCase() : 'HR'}
                        </div>
                        <div>
                            <div class="font-bold text-sm text-white/80 group-hover:text-white">${r.full_name || r.email}</div>
                            <div class="text-[10px] font-mono text-white/20 uppercase">${r.email}</div>
                        </div>
                    </div>
                </td>
                <td class="py-4 text-center font-mono text-sm text-white/60">${r.total_interviews || 0}</td>
                <td class="py-4 text-center">
                    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full ${r.avg_trust_score !== null ? 'bg-cyan-400/10 border-cyan-400/20 text-cyan-400' : 'bg-white/5 border-white/10 text-white/30'} border text-[10px] font-bold">
                        <i data-lucide="shield-check" class="w-3 h-3"></i>
                        ${r.avg_trust_score !== null ? r.avg_trust_score + '%' : '--'}
                    </div>
                </td>
                <td class="py-4 text-right">
                    <button class="p-2 rounded-lg bg-white/5 hover:bg-cyan-400 hover:text-obsidian transition-all select-recruiter-btn" data-id="${r.user_id}" data-name="${r.full_name || r.email}">
                        <i data-lucide="star" class="w-4 h-4"></i>
                    </button>
                </td>
            `;
            
            tr.querySelector('.select-recruiter-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                selectRecruiter(r.user_id, r.full_name || r.email);
            });
            
            tr.addEventListener('click', () => selectRecruiter(r.user_id, r.full_name || r.email));
            
            recruiterListBody.appendChild(tr);
        });
        
        if (window.lucide) lucide.createIcons();
    }

    function renderTeamAccessList(data) {
        const teamAccessList = document.getElementById('team-access-list');
        if (!teamAccessList) return;
        
        teamAccessList.innerHTML = '';
        
        if (data.length === 0) {
            teamAccessList.innerHTML = `<tr><td colspan="3" class="py-8 text-center text-white/20 italic">No members found in your organization.</td></tr>`;
            return;
        }

        data.forEach(r => {
            const tr = document.createElement('tr');
            tr.className = 'group hover:bg-white/5 transition-colors';
            
            const roleColor = r.role === 'MANAGER' ? 'text-purple-400 border-purple-400/20 bg-purple-400/10' : 'text-cyan-400 border-cyan-400/20 bg-cyan-400/10';
            
            tr.innerHTML = `
                <td class="py-4">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center font-bold text-[10px] text-white border border-white/10">
                            ${r.full_name ? r.full_name.substring(0, 2).toUpperCase() : 'HR'}
                        </div>
                        <div>
                            <div class="font-bold text-sm text-white/80">${r.full_name || r.email}</div>
                            <div class="text-[10px] font-mono text-white/20 uppercase">${r.email}</div>
                        </div>
                    </div>
                </td>
                <td class="py-4">
                    <div class="flex items-center gap-2">
                        <div class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md ${roleColor} text-[9px] font-bold">
                            ${r.role || 'HR_RECRUITER'}
                        </div>
                        <div class="flex items-center gap-1 ml-2">
                            <div class="w-1.5 h-1.5 rounded-full ${r.is_active ? 'bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.5)]' : 'bg-white/20'}"></div>
                            <span class="text-[9px] font-mono ${r.is_active ? 'text-emerald-400' : 'text-white/20'} uppercase tracking-widest">${r.is_active ? 'Online' : 'Offline'}</span>
                        </div>
                    </div>
                </td>
                <td class="py-4 text-right">
                    <button class="p-2 rounded-lg bg-white/5 hover:bg-red-500 hover:text-white transition-all text-white/40" onclick="window.removeMember('${r.user_id}')" title="Revoke Access">
                        <i data-lucide="user-x" class="w-4 h-4"></i>
                    </button>
                </td>
            `;
            teamAccessList.appendChild(tr);
        });
        
        if (window.lucide) lucide.createIcons();
    }

    window.removeMember = async function(userId) {
        if (!confirm('Are you sure you want to revoke access for this member?')) return;
        
        try {
            const response = await fetch(endpoint(`/api/manager/recruiters/${userId}`), { 
                method: 'DELETE',
                headers: authHeaders
            });
            if (response.ok) {
                fetchData(); // Reload
            } else {
                const err = await response.json();
                alert('Failed to remove: ' + (err.detail || 'Unknown error'));
            }
        } catch(e) {
            console.error('Error removing member:', e);
            alert('Failed to process request.');
        }
    };

    async function renderSecurityAlerts() {
        if (!securityAlertsContainer) return;

        securityAlertsContainer.innerHTML = `<div class="text-xs text-white/20 italic animate-pulse">Scanning for anomalies...</div>`;

        try {
            const res = await fetch(`${API_BASE}/api/manager/audit-logs`, { headers: authHeaders });
            const logs = res.ok ? await res.json() : [];
            
            if (logs.length === 0) {
                securityAlertsContainer.innerHTML = `<div class="text-xs text-white/20 italic">No critical anomalies detected in the last 24h.</div>`;
                return;
            }

            securityAlertsContainer.innerHTML = logs.slice(0, 5).map(log => {
                const severity = log.severity || 'info';
                const timeAgo = timeSince(new Date(log.created_at));
                const isHigh = severity.includes('CRITICAL') || severity.includes('OVERRIDE') || severity.includes('BYPASS') || severity.includes('error');
                const borderColor = isHigh ? 'border-red-500/20 hover:border-red-500/40' : 'border-yellow-500/10 hover:border-yellow-500/30';
                const textColor = isHigh ? 'text-red-400' : 'text-yellow-400';
                return `
                <div class="p-4 rounded-2xl bg-obsidian/40 border ${borderColor} flex flex-col gap-2 transition-all">
                    <div class="flex items-center justify-between">
                        <span class="text-[10px] font-mono ${textColor} font-bold">${severity.toUpperCase()}</span>
                        <span class="text-[10px] font-mono text-white/20">${timeAgo}</span>
                    </div>
                    <p class="text-xs text-white/60">${log.message || log.description || 'System event recorded.'}</p>
                </div>`;
            }).join('');
        } catch (e) {
            console.error('Failed to load security alerts:', e);
            securityAlertsContainer.innerHTML = `<div class="text-xs text-red-400/60 italic">Failed to load alerts.</div>`;
        }
    }

    async function fetchBillingData() {
        const billingPlanLabel = document.getElementById('billing-plan-label');
        const billingPlanPrice = document.getElementById('billing-plan-price');
        const billingNextDate = document.getElementById('billing-next-date');
        const billingStatus = document.getElementById('billing-status');
        const billingUsageBar = document.getElementById('billing-usage-bar');
        const billingUsageText = document.getElementById('billing-usage-text');
        const billingUsagePercent = document.getElementById('billing-usage-percent');
        const billingMaxDuration = document.getElementById('billing-max-duration');
        const billingMaxParticipants = document.getElementById('billing-max-participants');
        const billingTotalSessions = document.getElementById('billing-total-sessions');

        try {
            const res = await fetch(`${API_BASE}/api/manager/billing`, { headers: authHeaders });
            if (!res.ok) return;
            const data = await res.json();

            const used = data.interviews_used || 0;
            const limit = data.interviews_limit || 10;
            const pct = Math.min(100, Math.round((used / limit) * 100));
            const barColor = pct >= 90 ? 'bg-red-400' : pct >= 70 ? 'bg-yellow-400' : 'bg-cyan-400';

            if (billingPlanLabel) billingPlanLabel.textContent = data.plan_label || data.plan_id?.toUpperCase() || 'FREE';
            if (billingPlanPrice) billingPlanPrice.innerHTML = data.plan_price > 0 
                ? `$${data.plan_price}<span class="text-sm text-white/40 font-normal">/mo</span>` 
                : `<span class="text-sm text-white/60 font-normal">Free Plan</span>`;
            if (billingNextDate) billingNextDate.textContent = data.next_billing_date && data.next_billing_date !== 'N/A'
                ? `Next billing: ${new Date(data.next_billing_date).toLocaleDateString('en-GB', { day:'numeric', month:'short', year:'numeric' })}`
                : 'No upcoming billing';
            if (billingStatus) {
                billingStatus.textContent = data.status || 'ACTIVE';
                billingStatus.className = `px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest border ${
                    data.status === 'ACTIVE' ? 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20' 
                    : 'bg-red-400/10 text-red-400 border-red-400/20'
                }`;
            }
            if (billingUsageBar) {
                billingUsageBar.className = `h-full ${barColor} rounded-full transition-all duration-1000`;
                billingUsageBar.style.width = `${pct}%`;
            }
            if (billingUsageText) billingUsageText.textContent = `${used} / ${limit} Interviews`;
            if (billingUsagePercent) {
                billingUsagePercent.textContent = `${pct}%`;
                billingUsagePercent.className = `text-[10px] font-mono font-bold ${
                    pct >= 90 ? 'text-red-400' : pct >= 70 ? 'text-yellow-400' : 'text-cyan-400'
                }`;
            }
            // Telemetry panel
            if (billingMaxDuration) billingMaxDuration.textContent = data.max_duration_mins ?? '--';
            if (billingMaxParticipants) billingMaxParticipants.textContent = data.max_participants ?? '--';
            if (billingTotalSessions) billingTotalSessions.textContent = used;
        } catch (e) {
            console.error('Failed to load billing data:', e);
        }
    }

    // Expose for tab switching trigger
    window.refreshBillingTab = fetchBillingData;

    function timeSince(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }

    function selectRecruiter(id, name) {
        selectedRecruiterId = id;
        if (selectedRecruiterName) {
            selectedRecruiterName.textContent = name;
            selectedRecruiterName.classList.remove('italic', 'text-white/40');
            selectedRecruiterName.classList.add('text-cyan-400', 'font-bold');
        }
        if (submitEvalBtn) submitEvalBtn.disabled = false;
        
        if (window.innerWidth < 1024) {
            const evalConsole = document.getElementById('evaluation-console');
            if (evalConsole) evalConsole.scrollIntoView({ behavior: 'smooth' });
        }
    }

    function setRating(rating) {
        currentRating = rating;
        if (!starRatingContainer) return;
        const stars = starRatingContainer.querySelectorAll('.star-btn');
        stars.forEach((star, index) => {
            if (index < rating) {
                star.classList.add('bg-cyan-400/30', 'border-cyan-400/50', 'text-cyan-400');
            } else {
                star.classList.remove('bg-cyan-400/30', 'border-cyan-400/50', 'text-cyan-400');
            }
        });
    }

    if (evaluationForm) {
        evaluationForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!selectedRecruiterId || currentRating === 0) return;

            submitEvalBtn.disabled = true;
            submitEvalBtn.textContent = 'TRANSMITTING...';

            try {
                const response = await fetch(`${API_BASE}/api/manager/evaluate`, {
                    method: 'POST',
                    headers: authHeaders,
                    body: JSON.stringify({
                        recruiter_id: selectedRecruiterId,
                        rating_efficiency: currentRating,
                        rating_quality: currentRating,
                        notes: evalFeedback ? evalFeedback.value : ''
                    })
                });

                const result = await response.json();
                if (result.status === 'SUCCESS') {
                    submitEvalBtn.classList.add('bg-green-500');
                    submitEvalBtn.textContent = 'ASSESSMENT SECURED';
                    
                    setTimeout(() => {
                        submitEvalBtn.classList.remove('bg-green-500');
                        submitEvalBtn.textContent = 'POST EVALUATION';
                        submitEvalBtn.disabled = false;
                        evaluationForm.reset();
                        setRating(0);
                        if (selectedRecruiterName) {
                            selectedRecruiterName.textContent = 'Select a recruiter from the list';
                            selectedRecruiterName.classList.add('italic', 'text-white/40');
                        }
                        selectedRecruiterId = null;
                    }, 2000);
                }
            } catch (error) {
                console.error('Evaluation delivery failed:', error);
                submitEvalBtn.textContent = 'FAILED - RETRY';
                submitEvalBtn.disabled = false;
            }
        });
    }

    let performanceChart = null;
    function updateChart(data) {
        const canvas = document.getElementById('performanceChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const labels = data.map(r => r.full_name || r.email);
        const sessionCounts = data.map(r => r.total_interviews || 0);

        if (performanceChart) performanceChart.destroy();

        performanceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Sessions Conducted',
                    data: sessionCounts,
                    backgroundColor: 'rgba(34, 211, 238, 0.2)',
                    borderColor: 'rgba(34, 211, 238, 1)',
                    borderWidth: 2,
                    borderRadius: 8,
                    hoverBackgroundColor: 'rgba(34, 211, 238, 0.4)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: 'rgba(255,255,255,0.4)', font: { family: 'Space Mono', size: 10 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: 'rgba(255,255,255,0.4)', font: { family: 'Space Mono', size: 10 } }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // Global fetchManagerRooms function
    window.fetchManagerRooms = async function() {
        const listContainer = document.getElementById('manager-rooms-list');
        if (!listContainer) return;
        
        listContainer.innerHTML = `
            <div class="flex flex-col items-center justify-center py-20 opacity-50">
                <i data-lucide="loader-2" class="w-8 h-8 mb-4 animate-spin text-cyan-400"></i>
                <p class="text-xs font-mono uppercase tracking-[0.3em] text-white">Fetching Intelligence...</p>
            </div>
        `;
        if (window.lucide) lucide.createIcons();

        try {
            const response = await fetch(`${API_BASE}/api/manager/rooms`, { headers: authHeaders });
            if (!response.ok) throw new Error('Failed to fetch rooms');
            
            const rooms = await response.json();
            
            if (rooms.length === 0) {
                listContainer.innerHTML = `
                    <div class="flex flex-col items-center justify-center py-20 opacity-30 text-center">
                        <i data-lucide="inbox" class="w-12 h-12 mb-4"></i>
                        <p class="text-xs font-mono uppercase tracking-[0.2em] text-white/60">No sessions recorded.</p>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
                return;
            }

            listContainer.innerHTML = rooms.map(room => {
                const dateStr = new Date(room.created_at).toLocaleString('en-GB', {
                    year: 'numeric', month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit', hour12: true
                }).replace(',', '');
                
                const isCompleted = room.status === 'COMPLETED';
                const statusColor = isCompleted ? 'text-green-400 border-green-400/20 bg-green-400/10' : 'text-yellow-400 border-yellow-400/20 bg-yellow-400/10';
                
                const actionBtn = isCompleted 
                    ? `<button onclick="window.location.href='report.html?room=${room.share_code}'" class="flex-1 py-3 px-4 rounded-xl bg-cyan-400/10 border border-cyan-400/20 text-cyan-400 text-xs font-bold uppercase tracking-widest hover:bg-cyan-400 hover:text-obsidian transition-all text-center w-full md:w-auto">View Report</button>`
                    : `<button onclick="window.location.href='room.html?id=${room.share_code}'" class="flex-1 py-3 px-4 rounded-xl bg-white/5 border border-white/10 text-white/80 text-xs font-bold uppercase tracking-widest hover:bg-white/20 transition-all text-center w-full md:w-auto">Join Room</button>`;

                const creatorInitial = room.creator_name ? room.creator_name.charAt(0).toUpperCase() : 'H';

                return `
                    <div class="glass-panel p-6 rounded-2xl border border-white/5 shadow-lg group hover:border-white/20 transition-all flex flex-col md:flex-row gap-6 items-center">
                        <!-- Creator Info -->
                        <div class="flex items-center gap-4 min-w-[200px] w-full md:w-auto">
                            <div class="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-xl font-bold text-cyan-400 shrink-0">
                                ${creatorInitial}
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="font-bold text-white text-sm truncate">${room.creator_name || 'Unknown HR'}</div>
                                <div class="text-[10px] font-mono text-white/40 uppercase truncate">${room.name || 'Untitled Session'}</div>
                            </div>
                        </div>
                        
                        <!-- Metadata -->
                        <div class="flex-1 grid grid-cols-2 gap-4 w-full border-t border-white/5 pt-4 md:pt-0 md:border-t-0">
                            <div>
                                <div class="text-[10px] font-mono text-white/40 uppercase tracking-widest mb-1">Date</div>
                                <div class="text-xs font-mono text-white/80 flex items-center gap-2"><i data-lucide="calendar" class="w-3 h-3 text-cyan-400"></i> ${dateStr}</div>
                            </div>
                            <div>
                                <div class="text-[10px] font-mono text-white/40 uppercase tracking-widest mb-1">Room ID</div>
                                <div class="text-xs font-mono text-white/80 flex items-center gap-2"><i data-lucide="hash" class="w-3 h-3 text-cyan-400"></i> ${room.share_code ? room.share_code.substring(0, 8) : room.id.substring(0, 8)}</div>
                            </div>
                        </div>
                        
                        <!-- Status & Action -->
                        <div class="flex flex-col md:flex-row items-center justify-between md:justify-end gap-4 w-full md:w-auto border-t border-white/5 pt-4 md:pt-0 md:border-t-0 md:pl-6 md:border-l">
                            <div class="px-3 py-1 rounded-full border ${statusColor} text-[10px] font-bold uppercase tracking-widest w-full md:w-auto text-center">
                                ${room.status}
                            </div>
                            ${actionBtn}
                        </div>
                    </div>
                `;
            }).join('');
            if (window.lucide) lucide.createIcons();

        } catch (error) {
            console.error('Error fetching manager rooms:', error);
            listContainer.innerHTML = `
                <div class="flex flex-col items-center justify-center py-20 opacity-50 text-center">
                    <i data-lucide="alert-triangle" class="w-12 h-12 mb-4 text-red-400"></i>
                    <p class="text-xs font-mono uppercase tracking-[0.2em] text-red-400">Failed to load sessions.</p>
                    <button onclick="fetchManagerRooms()" class="mt-4 px-4 py-2 border border-red-400/20 text-red-400 rounded hover:bg-red-400/10 transition-all text-xs">Retry</button>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        }
    };

    // Run Initial Load
    fetchData();
});

// Global Tabs Logic
window.switchManagerTab = function(tabId) {
    // Hide all contents
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    
    // Reset all tabs styles
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('text-cyan-400', 'border-cyan-400');
        btn.classList.add('text-white/40', 'border-transparent');
    });

    // Show target content
    const targetContent = document.getElementById(`content-${tabId}`);
    if (targetContent) {
        targetContent.classList.remove('hidden');
    }

    // Highlight target tab
    const targetTab = document.getElementById(`tab-${tabId}`);
    if (targetTab) {
        targetTab.classList.remove('text-white/40', 'border-transparent');
        targetTab.classList.add('text-cyan-400', 'border-cyan-400');
    }

    // Trigger specific logic for tabs
    if (tabId === 'sessions' && window.fetchManagerRooms) {
        window.fetchManagerRooms();
    }
    if (tabId === 'billing' && window.refreshBillingTab) {
        window.refreshBillingTab();
    }
};

// --- Invite Member Modal ---
window.showInviteModal = async function() {
    const modal = document.getElementById('invite-modal');
    const modalBody = document.getElementById('invite-modal-body');
    const modalContent = document.getElementById('invite-modal-content');
    const inviteCodeInput = document.getElementById('invite-code-input');
    const modalOrgName = document.getElementById('modal-org-name');
    const copyBtn = document.getElementById('copy-invite-btn');
    const closeBtn = document.getElementById('close-invite-modal');
    
    if (!modal) return;

    // Show modal and reset state
    modal.classList.remove('hidden');
    modalBody.classList.remove('hidden');
    modalContent.classList.add('hidden');

    const closeModal = () => modal.classList.add('hidden');
    closeBtn.onclick = closeModal;
    modal.querySelector('.modal-overlay').onclick = closeModal;

    try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) return;

        const res = await fetch(`${API_BASE}/api/manager/invite-code`, {
            headers: { 
                'Authorization': `Bearer ${session.access_token}`,
                'Content-Type': 'application/json'
            }
        });

        if (res.ok) {
            const data = await res.json();
            const code = data.invite_code || data.org_id;
            
            if (inviteCodeInput) inviteCodeInput.value = code;
            if (modalOrgName) modalOrgName.textContent = data.org_name || 'your organization';
            
            modalBody.classList.add('hidden');
            modalContent.classList.remove('hidden');

            if (copyBtn) {
                copyBtn.onclick = () => {
                    navigator.clipboard.writeText(code).then(() => {
                        const originalText = copyBtn.textContent;
                        copyBtn.textContent = 'Copied!';
                        copyBtn.classList.replace('bg-cyan-400', 'bg-emerald-400');
                        setTimeout(() => {
                            copyBtn.textContent = originalText;
                            copyBtn.classList.replace('bg-emerald-400', 'bg-cyan-400');
                        }, 2000);
                    });
                };
            }
        } else {
            modalBody.innerHTML = `<p class="text-sm text-red-400">Failed to retrieve invite code. Make sure you have an organization set up.</p>`;
        }
    } catch (e) {
        console.error('Invite modal error:', e);
        if (modalBody) modalBody.innerHTML = `<p class="text-sm text-red-400/80">Error retrieving invite code.</p>`;
    }
};


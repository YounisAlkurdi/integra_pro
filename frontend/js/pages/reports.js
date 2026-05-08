/**
 * INTEGRA | Reports Protocol Engine
 * Handles neural archive synchronization and AI-driven telemetry visualization.
 */

import { supabase } from '../core/supabase-client.js';

const API_BASE = 'http://127.0.0.1:8000'; // Backend base URL

document.addEventListener("DOMContentLoaded", async () => {
    if (window.lucide) lucide.createIcons();

    // Elements
    const sidebarList = document.getElementById('interviews-sidebar-list');
    const emptyReport = document.getElementById('empty-report');
    const reportDetail = document.getElementById('report-detail');
    const actionButtons = document.getElementById('report-actions');
    const userAvatar = document.getElementById('user-avatar');

    // State
    let selectedNodeId = null;

    // --- 0. Initialize User Intel ---
    async function initUser() {
        const { data: { user } } = await supabase.auth.getUser();
        if (user && userAvatar) {
            const initials = user.user_metadata?.full_name?.split(' ').map(n => n[0]).join('').toUpperCase() || user.email[0].toUpperCase();
            userAvatar.innerHTML = `<div class="w-full h-full rounded-full bg-obsidian flex items-center justify-center text-[10px] font-bold uppercase">${initials}</div>`;
        }
    }

    // --- 1. Sync Archives From Supabase ---
    async function syncArchives() {
        // ✅ Security: Get current authenticated user first
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) {
            window.location.href = 'login.html';
            return;
        }

        const { data: nodes, error } = await supabase
            .from('nodes')
            .select('*')
            .eq('user_id', user.id)  // ✅ Only fetch THIS user's nodes
            .order('created_at', { ascending: false });

        if (error || !nodes || nodes.length === 0) {
            sidebarList.innerHTML = `
                <div class="px-10 py-16 text-center opacity-30">
                    <p class="text-[9px] font-mono uppercase tracking-[0.3em]">No Neural Data Found</p>
                </div>
            `;
            return;
        }

        sidebarList.innerHTML = nodes.map(node => `
            <div class="interview-item p-8 border-b border-white/5 group" onclick="window.viewArchive('${node.room_id}')" id="archive-${node.room_id}">
                <div class="flex items-center gap-5">
                    <div class="w-12 h-12 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-center font-black text-cyan-400 group-hover:shadow-[0_0_15px_rgba(34,211,238,0.2)] transition-all">
                        ${node.candidate_name[0]}
                    </div>
                    <div>
                        <h4 class="text-xs font-black uppercase tracking-tight italic">${node.candidate_name}</h4>
                        <div class="flex items-center gap-2 mt-2">
                             <div class="w-1.5 h-1.5 rounded-full bg-emerald-500/40"></div>
                             <p class="text-[8px] font-mono text-white/30 uppercase tracking-[0.2em]">${node.position}</p>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        // Auto-load specific report if room ID is in URL
        const urlParams = new URLSearchParams(window.location.search);
        const autoRoomId = urlParams.get('room');
        if (autoRoomId) {
            // Slight delay to ensure DOM is ready
            setTimeout(() => {
                window.viewArchive(autoRoomId);
                // Optionally clean up the URL to look cleaner after loading
                window.history.replaceState({}, document.title, window.location.pathname);
            }, 100);
        }
    }

    // --- 2. Decrypt & Visualize Report ---
    window.viewArchive = async (nodeId) => {
        selectedNodeId = nodeId;

        // Visual Feedback
        document.querySelectorAll('.interview-item').forEach(el => el.classList.remove('active'));
        document.getElementById(`archive-${nodeId}`)?.classList.add('active');

        const emptyReport = document.getElementById('empty-report');
        const reportDetail = document.getElementById('report-detail');
        const actionButtons = document.getElementById('report-actions');

        emptyReport.classList.add('hidden');
        reportDetail.classList.remove('hidden');
        actionButtons.classList.remove('hidden');
        actionButtons.classList.add('flex');

        // Reset display
        reportDetail.style.opacity = '0';
        setTimeout(() => reportDetail.style.opacity = '1', 50);

        try {
            // ✅ Security: Re-verify user ownership
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) { window.location.href = 'login.html'; return; }

            // 1. Fetch Node Core Data
            const { data: node, error: nodeError } = await supabase
                .from('nodes')
                .select('*')
                .eq('room_id', nodeId)
                .eq('user_id', user.id)
                .single();
            if (nodeError || !node) {
                showToast("Access Denied: Node not in your archive", "error");
                return;
            }

            // 2. Fetch Detailed Forensic Report (The new columns we added)
            const { data: forensicReport } = await supabase
                .from('interview_reports')
                .select('*')
                .eq('room_id', nodeId)
                .maybeSingle();

            // 3. Fetch Session Join Data (Biometrics)
            const { data: joinReq } = await supabase
                .from('join_requests')
                .select('*')
                .eq('room_id', nodeId)
                .order('created_at', { ascending: false })
                .limit(1)
                .maybeSingle();

            // 4. Fetch Transcript Logs
            const { data: chatLogs } = await supabase
                .from('chat_logs')
                .select('*')
                .eq('room_id', nodeId)
                .order('created_at', { ascending: true });

            // Update Header
            document.getElementById('rep-name').innerText = node.candidate_name;
            document.getElementById('rep-position').innerText = `${node.position} • NEURAL NODE`;
            document.getElementById('rep-avatar').innerText = node.candidate_name[0];
            document.getElementById('rep-date').innerText = `TIMESTAMP: ${new Date(node.created_at).toLocaleString()}`;
            document.getElementById('report-id-display').innerText = `NODE-${nodeId.substring(0, 8).toUpperCase()}`;

            // Get auth token for backend requests
            const { data: { session } } = await supabase.auth.getSession();
            const token = session?.access_token;

            // Neural Visualization
            visualizeNeuralData(node, forensicReport, joinReq, chatLogs, token);
            showToast("Archive Decrypted Successfully", "success");
        } catch (e) {
            console.error("Neural Retrieval Failed:", e);
            showToast("Failed to Decrypt Node Data", "error");
        }
    };

    let forensicChartInstance = null;

    async function visualizeNeuralData(node, forensicReport, joinReq, chatLogs, token) {
        // 1. Data Mapping (Strict mapping - no misleading fallbacks)
        const focusScore = forensicReport?.focus_score_avg;
        const threatLevel = forensicReport?.threat_level_final;
        const aiProb = forensicReport?.ai_generated_prob;
        
        const integrityRisk = forensicReport?.integrity_risk_score;
        const linguisticConsist = forensicReport?.linguistic_consistency;
        const syntaxVar = forensicReport?.syntax_variance;
        const metaIntegrity = forensicReport?.metadata_integrity;

        const hasData = (forensicReport !== null && forensicReport !== undefined);
        
        // Update Stats Cards
        document.getElementById('rep-overall').innerText = hasData ? Math.round(100 - (integrityRisk || 0)) : '--';
        document.getElementById('rep-focus').innerText = focusScore !== undefined ? Math.round(focusScore) + '%' : '0%';
        document.getElementById('rep-threat').innerText = threatLevel || 'N/A';
        document.getElementById('rep-nlp').innerText = aiProb !== undefined ? Math.round(aiProb) + '%' : '0%';

        // Set Threat Colors
        const threatEl = document.getElementById('rep-threat');
        if (threatLevel === 'HIGH') {
            threatEl.className = 'text-2xl md:text-4xl font-black tracking-tighter text-red-500 uppercase italic';
        } else if (threatLevel === 'MEDIUM') {
            threatEl.className = 'text-2xl md:text-4xl font-black tracking-tighter text-yellow-400 uppercase italic';
        } else {
            threatEl.className = 'text-2xl md:text-4xl font-black tracking-tighter text-emerald-400 uppercase italic';
        }

        // Risk Badge & Hash
        const riskBadge = document.getElementById('rep-risk-badge');
        const hashEl = document.getElementById('rep-hash');
        if (hashEl) hashEl.innerText = `0x${btoa(node.room_id).substring(0, 16).toUpperCase()}`;

        if (!hasData) {
            riskBadge.className = 'px-10 py-4 rounded-2xl border border-white/10 text-[11px] font-black uppercase tracking-[0.4em] bg-white/5 text-white/40';
            riskBadge.innerText = 'NO DATA DETECTED';
        } else if (integrityRisk > 40) {
            riskBadge.className = 'px-10 py-4 rounded-2xl border border-red-500/20 text-[11px] font-black uppercase tracking-[0.4em] bg-red-500/10 text-red-500';
            riskBadge.innerText = 'CRITICAL ANOMALY';
        } else if (integrityRisk > 15) {
            riskBadge.className = 'px-10 py-4 rounded-2xl border border-yellow-500/20 text-[11px] font-black uppercase tracking-[0.4em] bg-yellow-500/10 text-yellow-500';
            riskBadge.innerText = 'ELEVATED RISK';
        } else {
            riskBadge.className = 'px-10 py-4 rounded-2xl border border-emerald-500/20 text-[11px] font-black uppercase tracking-[0.4em] bg-emerald-500/10 text-emerald-500';
            riskBadge.innerText = 'STABLE NODE';
        }

        // 2. Forensic Components Breakdown (Updated for 5 components)
        const nlp = forensicReport?.nlp_scores || {};
        const components = {
            lexical: Math.round((nlp.lexical || 0) * 100),
            syntactic: Math.round((nlp.syntactic || 0) * 100),
            metadata: Math.round(metaIntegrity || 0),
            variance: Math.round(syntaxVar || 0),
            consistency: Math.round(linguisticConsist || 0)
        };

        Object.keys(components).forEach(comp => {
            const score = components[comp];
            const scoreEl = document.getElementById(`score-${comp}`);
            const barEl = document.getElementById(`bar-${comp}`);
            if (scoreEl) scoreEl.innerText = score + '%';
            if (barEl) barEl.style.width = score + '%';
        });

        // 3. Initialize Forensic Chart
        initForensicChart(forensicReport);

        // 4. AI Summary Section (Enhanced)
        const aiContainer = document.getElementById('ai-report-container');
        // Forensic report URL is actually in join_requests table
        const forensicImageUrl = joinReq?.forensic_report_url;

        if (forensicReport && (forensicReport.ai_summary || forensicImageUrl)) {
            const verdict = nlp_results_verdict(aiProb, integrityRisk);
            
            let htmlContent = '<div class="space-y-6">';
            
            if (forensicReport.ai_summary) {
                htmlContent += `
                    <p class="text-white/80 italic text-sm border-l-2 border-cyan-400 pl-4 py-1">"${forensicReport.ai_summary}"</p>
                    <div class="grid grid-cols-1 gap-3">
                        <div class="p-4 bg-white/5 rounded-2xl border border-white/5">
                            <h5 class="text-[9px] font-mono text-cyan-400 uppercase tracking-widest mb-2">Neural Verdict</h5>
                            <p class="text-[11px] text-white/60">${verdict}</p>
                        </div>
                        <div class="flex items-center justify-between px-2">
                            <div class="flex items-center gap-2">
                                <div class="w-1.5 h-1.5 rounded-full ${focusScore > 70 ? 'bg-emerald-500' : 'bg-red-500'}"></div>
                                <span class="text-white/40 uppercase tracking-widest text-[8px]">Cognitive Focus: ${focusScore > 70 ? 'High' : 'Erratic'}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <div class="w-1.5 h-1.5 rounded-full ${aiProb < 30 ? 'bg-emerald-500' : 'bg-yellow-500'}"></div>
                                <span class="text-white/40 uppercase tracking-widest text-[8px]">Authenticity: ${aiProb < 30 ? 'Verified' : 'Flagged'}</span>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            htmlContent += '</div>';
            aiContainer.innerHTML = htmlContent;
        } else {
            aiContainer.innerHTML = `
                <div class="flex flex-col items-center justify-center py-10 opacity-20">
                    <i data-lucide="brain-circuit" class="w-8 h-8 mb-4"></i>
                    <p class="text-[9px] font-mono uppercase tracking-widest">Processing Intelligence...</p>
                </div>
            `;
        }

        // 5. Video & Forensic Image Evidence
        const videoEl = document.getElementById('verification-video');
        const videoPlaceholder = document.getElementById('video-placeholder');
        const forensicImgContainer = document.getElementById('forensic-image-container');

        // Handle Forensic Image (Restored to Visual Evidence section)
        if (forensicImageUrl) {
            forensicImgContainer.innerHTML = `
                <div class="relative group/img overflow-hidden rounded-2xl border border-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.1)]">
                    <img src="${forensicImageUrl}" alt="Forensic Analysis" class="w-full h-auto object-cover transition-transform duration-700 group-hover/img:scale-110">
                    <div class="absolute inset-0 bg-gradient-to-t from-obsidian via-transparent to-transparent opacity-60"></div>
                    <div class="absolute bottom-4 left-4 flex items-center gap-2">
                        <div class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
                        <span class="text-[8px] font-mono text-white/60 uppercase tracking-widest">Visual Evidence: Layer 01</span>
                    </div>
                </div>
            `;
            forensicImgContainer.classList.remove('hidden');
        } else {
            forensicImgContainer.classList.add('hidden');
            forensicImgContainer.innerHTML = '';
        }
        
        // Prevents redundant requests if already loaded or currently loading for this node
        if (joinReq && joinReq.verification_video_path) {
            if (videoEl.dataset.loadedNode === node.room_id || videoEl.dataset.loading === node.room_id) {
                return; 
            }

            videoEl.dataset.loading = node.room_id; // Set loading lock

            try {
                const sigRes = await fetch(
                    `${API_BASE}/api/nodes/signed-video-url?video_path=${encodeURIComponent(joinReq.verification_video_path)}`,
                    { headers: { 'Authorization': `Bearer ${token}` } }
                );
                if (sigRes.ok) {
                    const { signed_url } = await sigRes.json();
                    if (videoEl.dataset.loading === node.room_id) { // Verify node hasn't changed during fetch
                        videoEl.src = signed_url;
                        videoEl.load();
                        videoEl.dataset.loadedNode = node.room_id;
                        videoEl.classList.remove('hidden');
                        videoPlaceholder.classList.add('hidden');
                    }
                } else {
                    videoEl.classList.add('hidden');
                    videoPlaceholder.classList.remove('hidden');
                    videoEl.dataset.loadedNode = "";
                }
            } catch (e) {
                console.error("Video retrieval failed:", e);
                videoEl.classList.add('hidden');
                videoPlaceholder.classList.remove('hidden');
                videoEl.dataset.loadedNode = "";
            } finally {
                delete videoEl.dataset.loading; // Remove loading lock
            }
        } else {
            videoEl.src = "";
            videoEl.classList.add('hidden');
            videoPlaceholder.classList.remove('hidden');
            videoEl.dataset.loadedNode = "";
        }


        // 6. Neural Fingerprint Generation (WOW element)
        generateNeuralFingerprint(node.room_id, forensicReport?.neural_signature);

        // 5. Phone-Style Transcript
        const transcriptContainer = document.getElementById('transcript-container');
        if (chatLogs && chatLogs.length > 0) {
            transcriptContainer.innerHTML = chatLogs.map(log => {
                const s = log.sender?.toLowerCase() || '';
                const isHR = s.includes('#') || s.includes('hr') || s.includes('admin');
                
                return `
                    <div class="flex flex-col ${isHR ? 'items-end' : 'items-start'} gap-1">
                        <div class="max-w-[85%] px-4 py-3 rounded-2xl text-[11px] leading-relaxed shadow-lg transition-all hover:scale-[1.02] ${isHR 
                            ? 'bg-cyan-500 text-obsidian font-medium rounded-tr-none shadow-cyan-500/10' 
                            : 'bg-white/10 text-white/90 border border-white/5 rounded-tl-none shadow-black/20'}">
                            ${log.message}
                        </div>
                        <span class="text-[7px] font-mono text-white/20 uppercase tracking-widest px-2">${new Date(log.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
                    </div>
                `;
            }).join('');
            // Scroll to bottom
            transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
        } else {
            transcriptContainer.innerHTML = `<div class="h-full flex items-center justify-center text-white/10 text-[10px] uppercase tracking-widest italic">Encrypted Silence</div>`;
        }

        if (window.lucide) lucide.createIcons();
    }

    function initForensicChart(report) {
        const ctx = document.getElementById('forensicChart');
        if (!ctx) return;

        if (forensicChartInstance) {
            forensicChartInstance.destroy();
        }

        const series = report?.forensic_data_series || [];
        const labels = series.length > 0 ? series.map((_, i) => `${i}s`) : ['0s', '10s', '20s', '30s', '40s', '50s', '60s'];
        const focusData = series.length > 0 ? series.map(d => d.focus) : [0, 0, 0, 0, 0, 0, 0];
        const threatData = series.length > 0 ? series.map(d => d.threat) : [0, 0, 0, 0, 0, 0, 0];

        forensicChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'NEURAL FOCUS',
                        data: focusData,
                        borderColor: '#22d3ee',
                        backgroundColor: 'rgba(34, 211, 238, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 0,
                        pointHoverRadius: 5
                    },
                    {
                        label: 'THREAT PROBABILITY',
                        data: threatData,
                        borderColor: '#f43f5e',
                        backgroundColor: 'rgba(244, 63, 94, 0.05)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        borderDash: [5, 5],
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(10, 10, 10, 0.9)',
                        titleFont: { family: 'Space Mono', size: 10 },
                        bodyFont: { family: 'Space Mono', size: 10 },
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: 'rgba(255, 255, 255, 0.2)', font: { size: 8, family: 'Space Mono' } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: 'rgba(255, 255, 255, 0.2)', font: { size: 8, family: 'Space Mono' } }
                    }
                }
            }
        });
    }

    function showToast(msg, type) {
        const toast = document.getElementById('toast');
        const indicator = document.getElementById('toast-indicator');
        const text = document.getElementById('toast-msg');

        if (!toast) return;

        indicator.className = `w-2 h-2 rounded-full ${type === 'success' ? 'bg-cyan-400' : 'bg-red-500'}`;
        text.innerText = msg;
        
        toast.classList.remove('translate-y-20', 'opacity-0', 'pointer-events-none');
        setTimeout(() => {
            toast.classList.add('translate-y-20', 'opacity-0', 'pointer-events-none');
        }, 4000);
    }

    function nlp_results_verdict(aiProb, integrityRisk) {
        if (aiProb > 70) return "High probability of synthetic text generation detected. Patterns suggest LLM structural consistency.";
        if (integrityRisk > 40) return "Multiple anomalies detected in behavioral and linguistic telemetry. Manual review highly recommended.";
        if (aiProb > 40) return "Mixed signals detected. Linguistic flow contains non-human variance markers.";
        return "Behavioral and linguistic signatures match established human baselines. Node integrity verified.";
    }

    function generateNeuralFingerprint(id, existingSig) {
        const container = document.getElementById('neural-fingerprint');
        const sigHashEl = document.getElementById('neural-sig-hash');
        if (!container) return;

        const seed = Array.from(id).reduce((acc, char) => acc + char.charCodeAt(0), 0);
        const sigHash = existingSig || `SIG-${btoa(id).substring(0, 24).toUpperCase()}`;
        if (sigHashEl) sigHashEl.innerText = sigHash;

        // Generate dynamic SVG fingerprint
        const paths = Array.from({length: 12}).map((_, i) => {
            const angle = (i / 12) * Math.PI * 2;
            const x1 = 50 + Math.cos(angle) * 10;
            const y1 = 50 + Math.sin(angle) * 10;
            const x2 = 50 + Math.cos(angle + (seed % 10) / 20) * 40;
            const y2 = 50 + Math.sin(angle + (seed % 10) / 20) * 40;
            return `<path d="M ${x1} ${y1} Q ${50 + Math.sin(seed+i)*10} ${50 + Math.cos(seed+i)*10} ${x2} ${y2}" stroke="currentColor" stroke-width="0.5" fill="none" class="text-cyan-400" />`;
        }).join('');

        container.innerHTML = `
            <svg viewBox="0 0 100 100" class="w-full h-full">
                <circle cx="50" cy="50" r="45" stroke="rgba(34, 211, 238, 0.1)" stroke-width="0.2" fill="none" />
                <circle cx="50" cy="50" r="30" stroke="rgba(34, 211, 238, 0.05)" stroke-width="0.2" fill="none" />
                ${paths}
                <circle cx="50" cy="50" r="5" fill="#22d3ee" class="animate-pulse" />
            </svg>
        `;
        
        // Also update the small avatar fingerprint
        const avatarContainer = document.getElementById('rep-avatar');
        if (avatarContainer) {
            const oldOverlay = avatarContainer.querySelector('.fingerprint-overlay');
            if (oldOverlay) oldOverlay.remove();

            const overlay = document.createElement('div');
            overlay.className = 'absolute inset-0 fingerprint-overlay opacity-30';
            overlay.innerHTML = `
                <svg viewBox="0 0 100 100" class="w-full h-full">
                    <circle cx="50" cy="50" r="40" stroke="white" stroke-width="0.2" fill="none" stroke-dasharray="2 2" />
                </svg>
            `;
            avatarContainer.style.position = 'relative';
            avatarContainer.appendChild(overlay);
        }
    }

    // --- System Setup ---
    initUser();
    syncArchives();
});

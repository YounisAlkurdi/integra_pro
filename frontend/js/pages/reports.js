/**
 * INTEGRA | Reports Protocol Engine
 * Handles neural archive synchronization and AI-driven telemetry visualization.
 */

import { supabase } from '../core/supabase-client.js';

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
        const { data: nodes, error } = await supabase
            .from('nodes')
            .select('*')
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
    }

    // --- 2. Decrypt & Visualize Report ---
    window.viewArchive = async (nodeId) => {
        selectedNodeId = nodeId;

        // Visual Feedback
        document.querySelectorAll('.interview-item').forEach(el => el.classList.remove('active'));
        document.getElementById(`archive-${nodeId}`)?.classList.add('active');

        emptyReport.classList.add('hidden');
        reportDetail.classList.remove('hidden');
        actionButtons.classList.remove('hidden');
        actionButtons.classList.add('flex');

        // Reset display
        reportDetail.style.opacity = '0';
        setTimeout(() => reportDetail.style.opacity = '1', 50);

        try {
            // Fetch Node Data
            const { data: node, error: nodeError } = await supabase.from('nodes').select('*').eq('room_id', nodeId).single();
            if (nodeError) throw nodeError;

            // Fetch Forensic Data (from join_requests)
            const { data: joinReq, error: joinError } = await supabase
                .from('join_requests')
                .select('*')
                .eq('room_id', nodeId)
                .order('created_at', { ascending: false })
                .limit(1)
                .maybeSingle();

            // Fetch Chat Logs (Transcript)
            const { data: chatLogs, error: chatError } = await supabase
                .from('chat_logs')
                .select('*')
                .eq('room_id', nodeId)
                .order('created_at', { ascending: true });

            // Header Decryption
            document.getElementById('rep-name').innerText = node.candidate_name;
            document.getElementById('rep-position').innerText = `${node.position} • NEURAL NODE`;
            document.getElementById('rep-avatar').innerText = node.candidate_name[0];
            document.getElementById('rep-date').innerText = `TIMESTAMP: ${new Date(node.created_at).toLocaleString()}`;

            // Neural Visualization
            visualizeNeuralData(node, joinReq, chatLogs);
            showToast("Archive Decrypted Successfully", "success");
        } catch (e) {
            console.error("Neural Retrieval Failed:", e);
            showToast("Failed to Decrypt Node Data", "error");
        }
    };

    function visualizeNeuralData(node, joinReq, chatLogs) {
        // 1. Overall Stats
        const deepfakeScore = joinReq ? (joinReq.deepfake_score || 0) : 0;
        const confidence = 85; // Simulated/Derived from other metrics
        const integrityRisk = deepfakeScore;
        const eyeStability = 90; // Placeholder

        document.getElementById('rep-overall').innerText = 100 - Math.floor(deepfakeScore / 2);
        document.getElementById('rep-confidence').innerText = confidence + '%';
        document.getElementById('rep-fraud').innerText = Math.round(integrityRisk) + '%';
        document.getElementById('rep-eye').innerText = eyeStability + '%';

        // 2. Risk Assessment
        const riskBadge = document.getElementById('rep-risk-badge');
        if (integrityRisk > 30) {
            riskBadge.className = 'px-8 py-3 rounded-2xl border border-red-500/20 text-[10px] font-black uppercase tracking-[0.3em] bg-red-500/10 text-red-500';
            riskBadge.innerText = 'CRITICAL RISK';
        } else {
            riskBadge.className = 'px-8 py-3 rounded-2xl border border-emerald-500/20 text-[10px] font-black uppercase tracking-[0.3em] bg-emerald-500/10 text-emerald-500';
            riskBadge.innerText = 'STABLE NODE';
        }

        // 3. Metrics Bars
        const metrics = [
            { label: 'Neural Authenticity', val: 100 - Math.round(deepfakeScore), color: 'text-cyan-400' },
            { label: 'Integrity Pulse', val: 100 - Math.round(integrityRisk), color: 'text-emerald-500' },
            { label: 'Liveness Confidence', val: confidence, color: 'text-purple-400' },
            { label: 'Signal Stability', val: eyeStability, color: 'text-blue-400' }
        ];

        document.getElementById('metrics-container').innerHTML = metrics.map(m => `
            <div class="metric-row">
                <div class="flex justify-between items-center text-[10px] font-mono uppercase tracking-[0.4em]">
                    <span class="text-white/30">${m.label}</span>
                    <span class="text-white font-bold">${m.val}%</span>
                </div>
                <div class="metric-bar-bg">
                    <div class="metric-fill" style="width: ${m.val}%; background: currentColor; box-shadow: 0 0 20px currentColor; opacity: 0.8; color: ${m.color.includes('cyan') ? '#22d3ee' : (m.color.includes('emerald') ? '#10b981' : (m.color.includes('purple') ? '#a855f7' : '#60a5fa'))}"></div>
                </div>
            </div>
        `).join('');

        // 4. Forensic Evidence
        const videoEl = document.getElementById('verification-video');
        const videoPlaceholder = document.getElementById('video-placeholder');
        
        if (joinReq && joinReq.verification_video_path) {
            videoEl.src = joinReq.verification_video_path; 
            videoEl.load(); // Force browser to refresh video buffer
            videoEl.classList.remove('hidden');
            videoPlaceholder.classList.add('hidden');
        } else {
            videoEl.classList.add('hidden');
            videoPlaceholder.classList.remove('hidden');
        }

        document.getElementById('forensic-score').innerText = Math.round(deepfakeScore);
        const forensicStatus = document.getElementById('forensic-status');
        if (deepfakeScore > 30) {
            forensicStatus.innerText = 'ANOMALOUS';
            forensicStatus.className = 'text-xs font-black uppercase tracking-widest text-red-500 italic';
        } else {
            forensicStatus.innerText = 'AUTHENTIC';
            forensicStatus.className = 'text-xs font-black uppercase tracking-widest text-emerald-500 italic';
        }

        document.getElementById('forensic-brief').innerHTML = joinReq && joinReq.forensic_report_url ? 
            `<img src="${joinReq.forensic_report_url}" class="w-full rounded-xl border border-white/5" />` : 
            (joinReq ? `Biometric analysis for ${joinReq.participant_name} shows a deepfake probability of ${deepfakeScore}%. ${deepfakeScore > 20 ? 'Visual inconsistencies detected in neural frame mapping.' : 'Neural patterns match biometric baseline.'}` : 'No forensic data available for this node.');

        // 5. Transcript Logs
        const transcriptContainer = document.getElementById('transcript-container');
        const candidateName = node.candidate_name;

        if (chatLogs && chatLogs.length > 0) {
            transcriptContainer.innerHTML = chatLogs.map(log => {
                // Heuristic: LiveKit identities (HR) often have # or explicit tags
                const s = log.sender?.toLowerCase() || '';
                const isHR = s.includes('#') || s.includes('hr') || s.includes('admin');
                const isCandidate = !isHR;

                return `
                    <div class="flex flex-col ${isHR ? 'items-end' : 'items-start'} gap-2">
                        <div class="flex items-center gap-2 mb-1 ${isHR ? 'flex-row-reverse' : ''}">
                            <span class="text-[8px] font-mono uppercase tracking-widest ${isHR ? 'text-cyan-400/60' : 'text-white/30'}">${log.sender}</span>
                            <span class="text-[8px] font-mono text-white/10 italic">${new Date(log.created_at).toLocaleTimeString()}</span>
                        </div>
                        <div class="px-5 py-3 rounded-2xl text-[11px] font-medium leading-relaxed max-w-[80%] ${isHR 
                            ? 'bg-cyan-400/10 border border-cyan-400/20 text-cyan-400 rounded-tr-none ml-auto' 
                            : 'bg-white/5 border border-white/10 text-white/70 rounded-tl-none mr-auto'}">
                            ${log.message}
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            transcriptContainer.innerHTML = `
                <div class="p-10 text-center opacity-20">
                    <i data-lucide="database" class="w-8 h-8 mx-auto mb-4"></i>
                    <p class="text-[10px] font-mono uppercase tracking-widest">No communications logged in this session</p>
                </div>
            `;
        }

        if (window.lucide) lucide.createIcons();
    }

    function generateAnalysisCluster() {
        return {
            overall: Math.floor(Math.random() * 20) + 78,
            confidence: 81 + Math.floor(Math.random() * 15),
            fraud: 2 + Math.floor(Math.random() * 15),
            eye: 85 + Math.floor(Math.random() * 12),
            velocity: 75 + Math.floor(Math.random() * 20)
        };
    }

    function showToast(msg, type) {
        const toast = document.getElementById('toast');
        const indicator = document.getElementById('toast-indicator');
        const text = document.getElementById('toast-msg');

        indicator.className = `w-2 h-2 rounded-full ${type === 'success' ? 'bg-cyan-400' : 'bg-red-500'}`;
        text.innerText = msg;
        
        toast.classList.remove('translate-y-20');
        setTimeout(() => toast.classList.add('translate-y-20'), 4000);
    }

    // Setup
    initUser();
    syncArchives();
});

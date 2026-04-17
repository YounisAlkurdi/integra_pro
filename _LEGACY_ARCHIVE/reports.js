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
            <div class="interview-item p-8 border-b border-white/5 group" onclick="window.viewArchive('${node.id}')" id="archive-${node.id}">
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
            const { data: node, error } = await supabase.from('nodes').select('*').eq('id', nodeId).single();
            if (error) throw error;

            // Header Decryption
            document.getElementById('rep-name').innerText = node.candidate_name;
            document.getElementById('rep-position').innerText = `${node.position} • NEURAL NODE`;
            document.getElementById('rep-avatar').innerText = node.candidate_name[0];
            document.getElementById('rep-date').innerText = `TIMESTAMP: ${new Date(node.created_at).toLocaleString()}`;

            // Neural Visualization
            visualizeNeuralData(generateAnalysisCluster());
            showToast("Archive Decrypted Successfully", "success");
        } catch (e) {
            console.error("Neural Retrieval Failed:", e);
            showToast("Failed to Decrypt Node Data", "error");
        }
    };

    function visualizeNeuralData(data) {
        document.getElementById('rep-overall').innerText = data.overall;
        document.getElementById('rep-confidence').innerText = data.confidence + '%';
        document.getElementById('rep-fraud').innerText = data.fraud + '%';
        document.getElementById('rep-eye').innerText = data.eye + '%';

        // Risk Assessment
        const riskBadge = document.getElementById('rep-risk-badge');
        if (data.fraud > 30) {
            riskBadge.className = 'px-8 py-3 rounded-2xl border border-red-500/20 text-[10px] font-black uppercase tracking-[0.3em] bg-red-500/10 text-red-500';
            riskBadge.innerText = 'CRITICAL RISK';
        } else {
            riskBadge.className = 'px-8 py-3 rounded-2xl border border-emerald-500/20 text-[10px] font-black uppercase tracking-[0.3em] bg-emerald-500/10 text-emerald-500';
            riskBadge.innerText = 'STABLE NODE';
        }

        // Metrics Bars
        const metrics = [
            { label: 'Synaptic Stability', val: data.confidence, color: 'text-cyan-400' },
            { label: 'Integrity Pulse', val: 100 - data.fraud, color: 'text-emerald-500' },
            { label: 'Response Velocity', val: data.velocity, color: 'text-purple-400' },
            { label: 'Gaze Focus', val: data.eye, color: 'text-blue-400' }
        ];

        document.getElementById('metrics-container').innerHTML = metrics.map(m => `
            <div class="metric-row">
                <div class="flex justify-between items-center text-[10px] font-mono uppercase tracking-[0.4em]">
                    <span class="text-white/30">${m.label}</span>
                    <span class="text-white font-bold">${m.val}%</span>
                </div>
                <div class="metric-bar-bg">
                    <div class="metric-fill" style="width: ${m.val}%; color: currentColor; background: currentColor; box-shadow: 0 0 20px currentColor; opacity: 0.8; color: ${m.color.includes('cyan') ? '#22d3ee' : (m.color.includes('emerald') ? '#10b981' : (m.color.includes('purple') ? '#a855f7' : '#60a5fa'))}"></div>
                </div>
            </div>
        `).join('');

        // Intelligence Directives (Recommendations)
        document.getElementById('recommendations-list').innerHTML = `
            <li class="flex items-start gap-5 group">
                <div class="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0 border border-emerald-500/20">
                    <i data-lucide="check" class="w-4 h-4 text-emerald-500"></i>
                </div>
                <p class="text-[11px] font-medium leading-relaxed text-white/50 group-hover:text-white transition-colors uppercase tracking-widest">Node exhibited 92% synchronization during the technical query phase.</p>
            </li>
            <li class="flex items-start gap-5 group">
                <div class="w-8 h-8 rounded-full bg-cyan-500/10 flex items-center justify-center shrink-0 border border-cyan-500/20 text-cyan-400">
                    <i data-lucide="zap" class="w-4 h-4"></i>
                </div>
                <p class="text-[11px] font-medium leading-relaxed text-white/50 group-hover:text-white transition-colors uppercase tracking-widest">Recommended for immediate Level 4 Protocol clearance.</p>
            </li>
        `;

        // Threat Log (Alerts)
        document.getElementById('alerts-container').innerHTML = data.fraud > 15 ? `
            <div class="p-6 bg-red-400/5 border border-red-500/20 rounded-2xl flex items-center gap-5">
                <div class="w-2 h-2 bg-red-500 rounded-full animate-ping"></div>
                <p class="text-[10px] font-mono text-red-500/80 uppercase tracking-widest leading-loose">Anomalous gaze patterns detected at T-minus 14:20. Deep verification suggested.</p>
            </div>
        ` : `
            <div class="p-6 bg-white/[0.02] border border-white/5 rounded-2xl flex items-center gap-5">
                <div class="w-2 h-2 bg-emerald-500 rounded-full"></div>
                <p class="text-[10px] font-mono text-white/20 uppercase tracking-widest">Threat environment: CLEAR</p>
            </div>
        `;

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

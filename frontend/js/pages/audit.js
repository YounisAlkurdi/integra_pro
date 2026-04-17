import { supabase } from '../core/supabase-client.js';

const auditLogsBody = document.getElementById('audit-logs-body');
const refreshBtn = document.getElementById('refresh-logs');
const prevBtn = document.getElementById('prev-page');
const nextBtn = document.getElementById('next-page');

let currentPage = 0;
const pageSize = 15;

async function fetchAuditLogs() {
    try {
        auditLogsBody.innerHTML = `
            <tr>
                <td colspan="7" class="p-20 text-center opacity-20">
                    <div class="flex flex-col items-center gap-4">
                        <div class="animate-spin w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full"></div>
                        <p class="text-[10px] font-mono uppercase tracking-[0.3em]">Decrypting Records...</p>
                    </div>
                </td>
            </tr>
        `;

        const { data, error } = await supabase
            .from('audit_logs')
            .select('*')
            .order('created_at', { ascending: false })
            .range(currentPage * pageSize, (currentPage + 1) * pageSize - 1);

        if (error) throw error;

        if (data.length === 0) {
            auditLogsBody.innerHTML = `
                <tr>
                    <td colspan="7" class="p-20 text-center opacity-40 text-[10px] font-mono uppercase tracking-widest">
                        No security events recorded in this sector.
                    </td>
                </tr>
            `;
            return;
        }

        renderLogs(data);
    } catch (err) {
        console.error('Audit Fetch Error:', err);
        auditLogsBody.innerHTML = `
            <tr>
                <td colspan="7" class="p-20 text-center text-red-400 text-[10px] font-mono uppercase tracking-widest">
                    Failed to establish link to audit vault.
                </td>
            </tr>
        `;
    }
}

function renderLogs(logs) {
    auditLogsBody.innerHTML = logs.map(log => `
        <tr class="hover:bg-white/[0.02] transition-colors group">
            <td class="p-6 text-[10px] font-mono text-white/40 group-hover:text-white/60">
                ${new Date(log.created_at).toLocaleString()}
            </td>
            <td class="p-6">
                <span class="px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-widest border ${getSeverityStyles(log.severity)}">
                    ${log.severity || 'INFO'}
                </span>
            </td>
            <td class="p-6">
                <span class="px-3 py-1 rounded-md text-[9px] font-black uppercase tracking-widest ${getActionColor(log.action)} bg-opacity-10 border border-opacity-20 ${getActionBorderColor(log.action)}">
                    ${log.action}
                </span>
            </td>
            <td class="p-6 text-[11px] font-mono text-cyan-400/80">
                ${log.target_resource || 'SYSTEM'}
            </td>
            <td class="p-6 text-[10px] font-mono text-white/50 leading-relaxed max-w-xs truncate" title='${JSON.stringify(log.details)}'>
                ${formatDetails(log.details)}
            </td>
            <td class="p-6 text-[10px] font-mono text-white/30 truncate max-w-[150px]" title="${log.user_agent || 'Unknown'}">
                ${log.user_agent || 'N/A'}
            </td>
            <td class="p-6 text-[10px] font-mono text-white/20">
                ${log.ip_address || '0.0.0.0'}
            </td>
        </tr>
    `).join('');
}

function getSeverityStyles(severity) {
    switch(severity?.toUpperCase()) {
        case 'CRITICAL': return 'text-red-500 border-red-500/50 bg-red-500/10 shadow-[0_0_10px_rgba(239,68,68,0.2)]';
        case 'WARNING': return 'text-amber-400 border-amber-400/50 bg-amber-400/10';
        case 'INFO': return 'text-cyan-400 border-cyan-400/50 bg-cyan-400/10';
        default: return 'text-white/40 border-white/20 bg-white/5';
    }
}

function getActionColor(action) {
    if (action.includes('CREATE') || action.includes('START')) return 'text-green-400 bg-green-400 border-green-400';
    if (action.includes('DELETE') || action.includes('TERMINATE')) return 'text-red-400 bg-red-400 border-red-400';
    if (action.includes('CHAT') || action.includes('REQUEST')) return 'text-cyan-400 bg-cyan-400 border-cyan-400';
    return 'text-white/60 bg-white/10 border-white/20';
}

function getActionBorderColor(action) {
    if (action.includes('CREATE')) return 'border-green-400';
    if (action.includes('DELETE')) return 'border-red-400';
    return 'border-white/10';
}

function formatDetails(details) {
    if (!details) return '-';
    if (typeof details === 'string') return details;
    return Object.entries(details)
        .map(([k, v]) => `${k}: ${v}`)
        .join(' | ');
}

refreshBtn.addEventListener('click', () => {
    currentPage = 0;
    fetchAuditLogs();
});

prevBtn.addEventListener('click', () => {
    if (currentPage > 0) {
        currentPage--;
        fetchAuditLogs();
    }
});

nextBtn.addEventListener('click', () => {
    currentPage++;
    fetchAuditLogs();
});

// Init
fetchAuditLogs();

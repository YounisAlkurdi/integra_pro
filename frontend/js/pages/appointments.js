/**
 * Integra Temporal Protocol Engine
 * Handles real-time scheduling, calendar rendering, and node synchronization.
 */

class TemporalEngine {
    constructor() {
        this.currentDate = new Date();
        this.viewMode = 'weekly';
        this.nodes = [];
        this.user = null;

        this.init();
    }

    async init() {
        try {
            // 1. Initial UI Setup
            if (window.lucide) lucide.createIcons();
            this.startClock();
            this.updateAvatar().catch(() => {});

            // 2. Auth & Data
            if (typeof supabase !== 'undefined') {
                const { data: { session } } = await supabase.auth.getSession();
                if (!session) {
                    window.location.href = 'index.html';
                    return;
                }
                this.user = session.user;
                // 3. Sync data
                await this.syncNodes();
            }
        } catch (e) {
            console.error("Temporal init failed:", e);
        } finally {
            // 4. Always render the timeline and current date
            this.render();
            // 5. Activity Interval
            setInterval(() => this.updateNowLine(), 60000); 
            this.updateNowLine();
        }
    }

    // --- 1. Real-time Clock ---
    startClock() {
        const clockEl = document.getElementById('live-clock');
        const update = () => {
            const now = new Date();
            clockEl.textContent = now.toLocaleTimeString('en-US', { 
                hour12: false, 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
        };
        setInterval(update, 1000);
        update();
    }

    async updateAvatar() {
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (user) {
                const avatar = document.getElementById('user-avatar-sidebar');
                if (avatar) {
                    const initials = user.user_metadata?.full_name?.split(' ').map(n => n[0]).join('').toUpperCase() || user.email[0].toUpperCase();
                    avatar.innerHTML = `<div class="w-full h-full rounded-full bg-obsidian flex items-center justify-center text-[10px] font-bold">${initials}</div>`;
                }
            }
        } catch (e) {}
    }

    // --- 2. Data Synchronization ---
    async syncNodes() {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            const res = await fetch(window.INTEGRA_SETTINGS.endpoint('/api/nodes'), {
                headers: { 'Authorization': `Bearer ${session.access_token}` }
            });
            this.nodes = await res.json();
        } catch (e) {
            console.error("Temporal Sync Failed:", e);
        }
    }

    // --- 3. Rendering Logic ---
    render() {
        this.renderHeader();
        this.renderGrid();
        this.renderQueue();
        if (window.lucide) lucide.createIcons();
    }

    renderHeader() {
        const periodEl = document.getElementById('current-period');
        const headerContainer = document.getElementById('calendar-header');
        
        // Update Title
        const options = { month: 'long', year: 'numeric' };
        periodEl.textContent = this.currentDate.toLocaleDateString('en-US', options);

        // Render Day Columns
        const startOfWeek = this.getStartOfWeek(this.currentDate);
        headerContainer.innerHTML = `<div class="p-6 border-r border-white/5 flex items-center justify-center font-mono text-[9px] uppercase tracking-widest text-white/20">Protocol</div>`;
        
        for (let i = 0; i < 7; i++) {
            const day = new Date(startOfWeek);
            day.setDate(startOfWeek.getDate() + i);
            
            const isToday = day.toDateString() === new Date().toDateString();
            
            const dayDiv = document.createElement('div');
            dayDiv.className = `p-8 flex flex-col items-center justify-center border-r border-white/5 transition-all ${isToday ? 'bg-cyan-400/5' : ''}`;
            dayDiv.innerHTML = `
                <span class="text-[9px] font-mono uppercase tracking-[0.2em] mb-2 ${isToday ? 'text-cyan-400' : 'text-white/20'}">${day.toLocaleDateString('en-US', { weekday: 'short' })}</span>
                <span class="text-2xl font-black italic tracking-tighter ${isToday ? 'text-cyan-400' : 'text-white/60'}">${day.getDate()}</span>
            `;
            headerContainer.appendChild(dayDiv);
        }
    }

    renderGrid() {
        const body = document.getElementById('calendar-body');
        // Clear previous grid but keep the now-line
        const nowLine = document.getElementById('now-line');
        body.innerHTML = '';
        body.appendChild(nowLine);

        // Time slots (8:00 to 22:00)
        for (let hour = 8; hour <= 22; hour++) {
            const row = document.createElement('div');
            row.className = 'grid grid-cols-8 border-b border-white/5 group';
            
            // Time label
            const timeLabel = document.createElement('div');
            timeLabel.className = 'h-24 border-r border-white/5 flex items-start justify-center pt-4 font-mono text-[10px] text-white/10 group-hover:text-cyan-400 transition-colors tabular-nums';
            timeLabel.textContent = `${hour.toString().padStart(2, '0')}:00`;
            row.appendChild(timeLabel);

            // Day cells
            const startOfWeek = this.getStartOfWeek(this.currentDate);
            for (let i = 0; i < 7; i++) {
                const day = new Date(startOfWeek);
                day.setDate(startOfWeek.getDate() + i);
                
                const cell = document.createElement('div');
                cell.className = 'h-24 border-r border-white/5 relative p-1 group/cell hover:bg-white/[0.01] transition-all';
                
                // Check for nodes in this slot
                const slotNodes = this.nodes.filter(n => {
                    if (!n.scheduled_at) return false;
                    const nDate = new Date(n.scheduled_at);
                    return nDate.toDateString() === day.toDateString() && nDate.getHours() === hour;
                });

                slotNodes.forEach(node => {
                    cell.appendChild(this.createNodeElement(node));
                });

                row.appendChild(cell);
            }
            body.appendChild(row);
        }
    }

    createNodeElement(node) {
        const div = document.createElement('div');
        
        const nDate = new Date(node.scheduled_at);
        const minutes = nDate.getMinutes();
        const topPercent = (minutes / 60) * 100;
        
        // Z-index trick: items further down in the hour have higher base z-index so they aren't covered completely
        div.className = 'absolute left-1 right-1 rounded-xl border p-2 flex flex-col justify-between cursor-pointer transition-all hover:scale-[1.02] hover:shadow-2xl hover:z-50 glass-panel overflow-hidden';
        div.style.zIndex = 10 + Math.floor(minutes/10);
        
        // Accurate visual timeline shift
        div.style.top = `calc(${topPercent}% + 2px)`; // 2px margin from top
        div.style.height = `calc(100% - 4px)`; // Block size is approximately 1 hour
        
        // Status Colors logic: only dim if 1 hour has passed AND it's not active
        const msSinceStart = new Date().getTime() - nDate.getTime();
        const isPast = msSinceStart > (60 * 60 * 1000) && node.status !== 'active';
        
        let statusClass = 'border-cyan-400/20 bg-cyan-400/5 shadow-[0_0_20px_rgba(34,211,238,0.05)]';
        
        if (isPast) {
            statusClass = 'border-white/10 bg-white/5';
        }
        
        if (node.status === 'active') { // Vibrant active mode
            statusClass = 'border-cyan-400/50 bg-cyan-400/10 shadow-[0_0_30px_rgba(34,211,238,0.15)] ring-1 ring-cyan-400/20';
        }

        div.className += ` ${statusClass}`;
        div.onclick = () => window.location.href = `integra-session.html?room=${node.room_id}&role=hr`;

        const timeStr = nDate.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', hour12:true});

        div.innerHTML = `
            <div class="flex flex-col">
                <div class="flex items-center justify-between mb-1">
                    <span class="text-[9px] font-mono font-black text-white/90 tracking-wide">${timeStr}</span>
                    <div class="w-1.5 h-1.5 rounded-full ${node.status === 'active' ? 'bg-cyan-400 animate-pulse' : 'bg-white/20'}"></div>
                </div>
                <span class="text-[10px] font-black uppercase text-white truncate leading-tight">${node.candidate_name || 'Subject Unknown'}</span>
                <span class="text-[8px] font-mono text-cyan-400/60 uppercase tracking-widest mt-0.5 truncate">${node.position || 'N/A'}</span>
            </div>
            <div class="mt-1 pt-1 border-t border-white/5 flex items-center justify-between">
                <span class="text-[7px] font-mono text-white/20 uppercase tracking-widest truncate">${node.room_id.substring(0,8)}</span>
            </div>
        `;
        return div;
    }

    renderQueue() {
        const queueContainer = document.getElementById('today-queue');
        const todayNodes = this.nodes
            .filter(n => new Date(n.scheduled_at).toDateString() === new Date().toDateString())
            .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at));

        if (todayNodes.length === 0) {
            queueContainer.innerHTML = `
                <div class="text-center py-20 opacity-20">
                    <i data-lucide="clock" class="w-12 h-12 mb-4 mx-auto"></i>
                    <p class="text-[10px] font-mono uppercase tracking-widest">Awaiting Transmissions</p>
                </div>
            `;
            return;
        }

        queueContainer.innerHTML = todayNodes.map(n => {
            const time = new Date(n.scheduled_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
            const isCompleted = new Date(n.scheduled_at) < new Date();
            const isActive = n.status === 'active';

            return `
                <div class="p-5 rounded-2xl bg-white/5 border border-white/5 hover:border-cyan-400/20 transition-all cursor-pointer group" onclick="window.location.href='integra-session.html?room=${n.room_id}&role=hr'">
                    <div class="flex items-start justify-between mb-3">
                        <span class="text-xl font-mono font-black text-white/20 group-hover:text-cyan-400 transition-colors tabular-nums">${time}</span>
                        <div class="flex items-center gap-2">
                             ${isActive ? '<span class="px-2 py-1 bg-cyan-400/10 text-cyan-400 text-[8px] font-black uppercase tracking-widest rounded border border-cyan-400/20">Active</span>' : ''}
                             <div class="w-1.5 h-1.5 rounded-full ${isActive ? 'bg-cyan-400 animate-ping' : 'bg-white/10'}"></div>
                        </div>
                    </div>
                    <div class="flex flex-col">
                        <span class="text-[11px] font-black uppercase tracking-tight text-white mb-1">${n.candidate_name || 'Unidentified'}</span>
                        <div class="flex items-center gap-2">
                            <i data-lucide="cpu" class="w-2.5 h-2.5 text-white/20"></i>
                            <span class="text-[8px] font-mono text-white/30 uppercase tracking-[0.2em]">${n.position || 'Security Protocol'}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    updateNowLine() {
        const line = document.getElementById('now-line');
        const body = document.getElementById('calendar-body');
        const now = new Date();
        const startOfWeek = this.getStartOfWeek(this.currentDate);
        const endOfWeek = new Date(startOfWeek);
        endOfWeek.setDate(startOfWeek.getDate() + 7);

        if (now >= startOfWeek && now < endOfWeek) {
            const hour = now.getHours();
            const minutes = now.getMinutes();
            
            if (hour >= 8 && hour <= 22) {
                const hourHeight = 96; // 6rem / h-24
                const top = (hour - 8 + minutes / 60) * hourHeight;
                line.style.top = top + 'px';
                line.classList.remove('hidden');
                
                // Horizontal offset based on day
                const dayIndex = (now.getDay() + 6) % 7; // Monday = 0
                // Wait, Monday is not always index 0. Let's align with our getStartOfWeek
                const colWidth = 100 / 8; // approx
                // The actual cols are 1/8 width roughly. 
                // Let's just keep it full width for now as it looks cooler like a timeline "scan"
            } else {
                line.classList.add('hidden');
            }
        } else {
            line.classList.add('hidden');
        }
    }

    // --- Helpers ---
    getStartOfWeek(date) {
        const d = new Date(date);
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust for Monday start
        d.setDate(diff);
        d.setHours(0, 0, 0, 0);
        return d;
    }

    prevWeek() {
        this.currentDate.setDate(this.currentDate.getDate() - 7);
        this.render();
    }

    nextWeek() {
        this.currentDate.setDate(this.currentDate.getDate() + 7);
        this.render();
    }
}

// Global Nav
window.prevWeek = () => window.engine.prevWeek();
window.nextWeek = () => window.engine.nextWeek();

document.addEventListener('DOMContentLoaded', () => {
    window.engine = new TemporalEngine();
});

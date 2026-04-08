/**
 * integra-session.js
 * Core logic for the interview session UI
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide Icons
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // Camera Access
    const videoElement = document.getElementById('local-video');
    const cameraPlaceholder = document.getElementById('camera-off-placeholder');
    let stream = null;

    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
                video: { width: 1280, height: 720 }, 
                audio: false 
            });
            videoElement.srcObject = stream;
        } catch (err) {
            console.error("Error accessing camera:", err);
            cameraPlaceholder.classList.remove('hidden');
            videoElement.classList.add('hidden');
        }
    }

    startCamera();

    // Controls
    let isMicOn = true;
    let isVideoOn = true;

    const micBtn = document.getElementById('toggle-mic');
    const videoBtn = document.getElementById('toggle-video');

    micBtn.addEventListener('click', () => {
        isMicOn = !isMicOn;
        micBtn.innerHTML = isMicOn ? '<i data-lucide="mic" class="w-6 h-6"></i>' : '<i data-lucide="mic-off" class="w-6 h-6 text-red-500"></i>';
        window.lucide.createIcons();
        micBtn.classList.toggle('bg-red-500/10', !isMicOn);
    });

    videoBtn.addEventListener('click', () => {
        isVideoOn = !isVideoOn;
        if (stream) {
            stream.getVideoTracks().forEach(track => track.enabled = isVideoOn);
        }
        videoBtn.innerHTML = isVideoOn ? '<i data-lucide="video" class="w-6 h-6"></i>' : '<i data-lucide="video-off" class="w-6 h-6 text-red-500"></i>';
        window.lucide.createIcons();
        videoBtn.classList.toggle('bg-red-500/10', !isVideoOn);
        
        cameraPlaceholder.classList.toggle('hidden', isVideoOn);
        videoElement.classList.toggle('hidden', !isVideoOn);
    });

    // Timer Logic
    let seconds = 30;
    const timerElement = document.getElementById('timer');

    function updateTimer() {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        timerElement.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        seconds++;
    }

    setInterval(updateTimer, 1000);

    // Sidebar Tab Switching
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabs = {
        stt: document.getElementById('stt-tab'),
        intel: document.getElementById('intel-tab')
    };

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-tab');
            
            // Toggle Buttons
            tabBtns.forEach(b => {
                b.classList.remove('active', 'text-white');
                b.classList.add('text-white/30');
            });
            btn.classList.add('active', 'text-white');
            btn.classList.remove('text-white/30');
            
            // Toggle Content
            Object.keys(tabs).forEach(id => {
                if (id === targetId) {
                    tabs[id].classList.remove('hidden');
                    tabs[id].classList.add('block');
                } else {
                    tabs[id].classList.add('hidden');
                    tabs[id].classList.remove('block');
                }
            });
        });
    });

    // Generate Audio Bars
    const audioBarsContainer = document.getElementById('audio-bars');
    const barCount = 40;
    for (let i = 0; i < barCount; i++) {
        const bar = document.createElement('div');
        bar.className = 'flex-1 bg-white/5 rounded-full transition-all duration-300';
        const height = Math.random() * 80 + 20;
        bar.style.height = `${height}%`;
        if (i % 5 === 0) {
            bar.classList.add('bg-cyan-400/20', 'animate-pulse');
            bar.style.animationDelay = `${i * 0.1}s`;
        }
        audioBarsContainer.appendChild(bar);
    }

    // Simulate Dynamic Bars
    setInterval(() => {
        const bars = audioBarsContainer.querySelectorAll('div');
        bars.forEach(bar => {
            if (!bar.classList.contains('bg-cyan-400/20')) {
                const height = Math.random() * 60 + 10;
                bar.style.height = `${height}%`;
            }
        });
    }, 150);

    // Initial Logs
    addSystemLog("SYSTEM: Forensic kernel initialized.");
    addSystemLog("AUDIO: High-fidelity capture stream active.");
    addSystemLog("VIDEO: Neural face mapping calibration pending.");
});

// Utility: Copy link
function copyInviteLink() {
    const sessionUrl = window.location.href;
    navigator.clipboard.writeText(sessionUrl).then(() => {
        showToast("Session link secured and copied");
    });
}

// Forensic Logic
function triggerCognitiveTest() {
    addSystemLog("INTEL: Triggering Cognitive Challenge Protocol...");
    showToast("Cognitive challenge sequence initiated");
    
    // Simulate some logic
    setTimeout(() => {
        addSystemLog("INTEL: Monitoring turn-latency for anomalies.");
    }, 1000);
}

function addSystemLog(message) {
    const logList = document.getElementById('log-list');
    if (!logList) return;

    // Clear placeholder if first log
    if (logList.innerHTML.includes('Initializing')) {
        logList.innerHTML = '';
    }

    const logEntry = document.createElement('div');
    logEntry.className = 'py-1 border-b border-white/5 flex items-start gap-3 opacity-0 translate-x-4 animate-in slide-in-from-right fade-in fill-mode-forwards duration-500';
    
    const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    logEntry.innerHTML = `
        <span class="text-white/20 shrink-0">[${time}]</span>
        <span class="${message.includes('INTEL') ? 'text-cyan-400' : 'text-white/60'}">${message}</span>
    `;
    
    logList.insertBefore(logEntry, logList.firstChild);
}

// Simple Toast Utility
function showToast(message) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'glass-panel px-8 py-5 rounded-2xl border border-cyan-400/20 text-[10px] font-mono text-cyan-400 uppercase tracking-widest font-black shadow-2xl animate-in slide-in-from-right fade-in duration-500';
    toast.innerHTML = `
        <div class="flex items-center gap-4">
            <div class="w-2 h-2 bg-cyan-400 rounded-full shadow-[0_0_10px_#22d3ee]"></div>
            ${message}
        </div>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('animate-out', 'fade-out', 'slide-out-to-right');
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

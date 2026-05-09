/**
 * Integra Executive Dashboard Logic
 * Managed by Antigravity AI
 */

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initial State
    let selectedRecruiterId = null;
    let currentRating = 0;
    const recruiters = [];

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
    for (let i = 1; i <= 5; i++) {
        const starClone = starTemplate.content.cloneNode(true);
        const btn = starClone.querySelector('button');
        btn.dataset.rating = i;
        btn.addEventListener('click', () => setRating(i));
        starRatingContainer.appendChild(starClone);
    }
    lucide.createIcons(); // Update icons for new stars

    // 4. Fetch Data Functions
    async function fetchData() {
        try {
            // Fetch stats
            const statsRes = await fetch('/api/manager/stats');
            const stats = await statsRes.json();
            
            // Update stats UI
            teamEfficiencyStat.textContent = `${stats.avg_candidate_score || 0}%`;
            teamSizeStat.textContent = stats.active_recruiters || 0;
            orgNameDisplay.textContent = `Organization: ${stats.org_name || 'Enterprise'}`;
            
            const inviteCodeElem = document.getElementById('org-invite-code-stat');
            if (inviteCodeElem && stats.org_id) {
                inviteCodeElem.textContent = stats.org_id;
                inviteCodeElem.dataset.code = stats.org_id;
            }

            // Fetch recruiters
            const recruiterRes = await fetch('/api/manager/recruiters');
            const recruiterData = await recruiterRes.json();
            renderRecruiterList(recruiterData);
            updateChart(recruiterData);

            // Fetch potential alerts (Mocking "Override" events for now)
            // In a real scenario, we'd have a specific endpoint for audit logs
            renderSecurityAlerts();

        } catch (error) {
            console.error('Failed to sync executive data:', error);
        }
    }

    function renderRecruiterList(data) {
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
                <td class="py-4 text-center font-mono text-sm text-white/60">${r.session_count || 0}</td>
                <td class="py-4 text-center">
                    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-400/10 border border-cyan-400/20 text-cyan-400 text-[10px] font-bold">
                        <i data-lucide="shield-check" class="w-3 h-3"></i>
                        ${r.avg_trust_score || '98'}%
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
        
        lucide.createIcons();
    }

    function renderSecurityAlerts() {
        // Mocking critical alerts to demonstrate the UI
        const mockAlerts = [
            { id: 1, type: 'CRITICAL OVERRIDE', recruiter: 'Ahmed H.', candidate: 'Jane Doe', time: '12m ago' },
            { id: 2, type: 'MANUAL BYPASS', recruiter: 'Sara M.', candidate: 'John Smith', time: '1h ago' }
        ];

        securityAlertsContainer.innerHTML = mockAlerts.map(alert => `
            <div class="p-4 rounded-2xl bg-obsidian/40 border border-red-500/10 flex flex-col gap-2 group hover:border-red-500/30 transition-all">
                <div class="flex items-center justify-between">
                    <span class="text-[10px] font-mono text-red-400 font-bold">${alert.type}</span>
                    <span class="text-[10px] font-mono text-white/20">${alert.time}</span>
                </div>
                <p class="text-xs text-white/60">
                    <span class="text-white font-bold">${alert.recruiter}</span> bypassed system for 
                    <span class="text-white">${alert.candidate}</span>.
                </p>
                <button class="w-full mt-2 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 text-[10px] font-bold border border-red-500/20 transition-all">
                    AUDIT LOGS
                </button>
            </div>
        `).join('');
    }

    // 5. Interaction Logics
    function selectRecruiter(id, name) {
        selectedRecruiterId = id;
        selectedRecruiterName.textContent = name;
        selectedRecruiterName.classList.remove('italic', 'text-white/40');
        selectedRecruiterName.classList.add('text-cyan-400', 'font-bold');
        submitEvalBtn.disabled = false;
        
        // Scroll to form on mobile
        if (window.innerWidth < 1024) {
            document.getElementById('evaluation-console').scrollIntoView({ behavior: 'smooth' });
        }
    }

    function setRating(rating) {
        currentRating = rating;
        const stars = starRatingContainer.querySelectorAll('.star-btn');
        stars.forEach((star, index) => {
            if (index < rating) {
                star.classList.add('bg-cyan-400/30', 'border-cyan-400/50', 'text-cyan-400');
            } else {
                star.classList.remove('bg-cyan-400/30', 'border-cyan-400/50', 'text-cyan-400');
            }
        });
    }

    evaluationForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!selectedRecruiterId || currentRating === 0) return;

        submitEvalBtn.disabled = true;
        submitEvalBtn.textContent = 'TRANSMITTING...';

        try {
            const response = await fetch('/api/manager/evaluate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recruiter_id: selectedRecruiterId,
                    rating_efficiency: currentRating,
                    rating_quality: currentRating, // Simplified for now
                    notes: evalFeedback.value
                })
            });

            const result = await response.json();
            if (result.status === 'SUCCESS') {
                // Success animation/feedback
                submitEvalBtn.classList.add('bg-green-500');
                submitEvalBtn.textContent = 'ASSESSMENT SECURED';
                
                setTimeout(() => {
                    submitEvalBtn.classList.remove('bg-green-500');
                    submitEvalBtn.textContent = 'POST EVALUATION';
                    submitEvalBtn.disabled = false;
                    evaluationForm.reset();
                    setRating(0);
                    selectedRecruiterName.textContent = 'Select a recruiter from the list';
                    selectedRecruiterName.classList.add('italic', 'text-white/40');
                    selectedRecruiterId = null;
                }, 2000);
            }
        } catch (error) {
            console.error('Evaluation delivery failed:', error);
            submitEvalBtn.textContent = 'FAILED - RETRY';
            submitEvalBtn.disabled = false;
        }
    });

    // 6. Chart.js Setup
    let performanceChart = null;
    function updateChart(data) {
        const ctx = document.getElementById('performanceChart').getContext('2d');
        const labels = data.map(r => r.full_name || r.email);
        const sessionCounts = data.map(r => r.session_count || 0);

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

    // Run Initial Load
    fetchData();
});

// Global copy function for the invite code
window.copyManagerInviteCode = function() {
    const inviteCodeElem = document.getElementById('org-invite-code-stat');
    if (inviteCodeElem && inviteCodeElem.dataset.code) {
        navigator.clipboard.writeText(inviteCodeElem.dataset.code).then(() => {
            const originalText = inviteCodeElem.textContent;
            inviteCodeElem.textContent = 'COPIED!';
            inviteCodeElem.classList.add('text-green-400');
            setTimeout(() => {
                inviteCodeElem.textContent = originalText;
                inviteCodeElem.classList.remove('text-green-400');
            }, 2000);
        }).catch(err => console.error('Failed to copy: ', err));
    }
};

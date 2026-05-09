/**
 * Integra Overseer (Admin) Logic
 * Managed by Antigravity AI
 */

document.addEventListener('DOMContentLoaded', async () => {
    // DOM Elements
    const globalOrgCount = document.getElementById('global-org-count');
    const globalUserCount = document.getElementById('global-user-count');
    const orgListBody = document.getElementById('org-list-body');
    const userAccessContainer = document.getElementById('user-access-container');
    
    const addOrgBtn = document.getElementById('add-org-btn');
    const orgModal = document.getElementById('org-modal');
    const closeModal = document.getElementById('close-modal');
    const orgForm = document.getElementById('org-form');

    // 1. Initial Data Fetch
    async function fetchSystemData() {
        try {
            // Fetch Organizations
            const orgsRes = await fetch('/api/admin/organizations');
            let orgs = [];
            if(orgsRes.ok) {
                orgs = await orgsRes.json();
                globalOrgCount.textContent = orgs.length;
                renderOrgs(orgs);
            }

            // Fetch Users (Access Registry)
            const usersRes = await fetch('/api/admin/users');
            let users = [];
            if(usersRes.ok) {
                users = await usersRes.json();
                globalUserCount.textContent = users.length;
                renderUsers(users, orgs);
            }

        } catch (error) {
            console.error('Failed to sync overseer data:', error);
        }
    }

    // 2. Rendering Functions
    function renderOrgs(orgs) {
        orgListBody.innerHTML = '';
        if (orgs.length === 0) {
            orgListBody.innerHTML = `<tr><td colspan="3" class="py-8 text-center text-white/20 italic">No organizations found.</td></tr>`;
            return;
        }

        orgs.forEach(org => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-white/5 transition-colors';
            
            let tierColor = 'text-white/40';
            if(org.subscription_tier === 'PRO') tierColor = 'text-cyan-400';
            if(org.subscription_tier === 'GOV') tierColor = 'text-amber-400';

            tr.innerHTML = `
                <td class="py-4">
                    <div class="font-bold text-sm">${org.name}</div>
                    <div class="text-[9px] font-mono text-white/40 mt-1 flex items-center gap-2">
                        ID: ${org.id.substring(0, 8)}...
                        <button onclick="navigator.clipboard.writeText('${org.id}'); alert('Invite Code Copied!');" class="hover:text-amber-400 transition-colors" title="Copy Invite Code">
                            <i data-lucide="copy" class="w-3 h-3"></i>
                        </button>
                    </div>
                </td>
                <td class="py-4 text-xs font-mono uppercase tracking-widest ${tierColor}">${org.subscription_tier || 'FREE'}</td>
                <td class="py-4 text-right">
                    <span class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-[10px] font-bold uppercase">
                        Active
                    </span>
                </td>
            `;
            orgListBody.appendChild(tr);
        });
    }

    function renderUsers(users, orgs) {
        userAccessContainer.innerHTML = '';
        if (users.length === 0) {
            userAccessContainer.innerHTML = `<div class="text-white/20 italic text-sm text-center py-4">No operators registered.</div>`;
            return;
        }

        users.forEach(user => {
            // Find org name if associated
            const org = orgs.find(o => o.id === user.org_id);
            const orgName = org ? org.name : 'Unassigned';
            
            let roleColor = 'text-white/40';
            if(user.role === 'MANAGER') roleColor = 'text-cyan-400';
            if(user.role === 'ADMIN') roleColor = 'text-amber-400';

            const div = document.createElement('div');
            div.className = 'p-4 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-between group hover:border-amber-500/30 transition-all';
            div.innerHTML = `
                <div>
                    <div class="text-sm font-bold">${user.user_id}</div>
                    <div class="flex gap-3 mt-1">
                        <span class="text-[10px] font-mono uppercase tracking-widest ${roleColor}">ROLE: ${user.role || 'RECRUITER'}</span>
                        <span class="text-[10px] font-mono text-white/20">| ORG: ${orgName}</span>
                    </div>
                </div>
                <button class="p-2 rounded-xl bg-white/5 border border-white/10 hover:bg-amber-400 hover:text-obsidian transition-all" title="Edit Access">
                    <i data-lucide="edit-3" class="w-4 h-4"></i>
                </button>
            `;
            
            // Edit access logic can be implemented here later
            div.querySelector('button').addEventListener('click', () => {
                alert(`Access Matrix Editor for ${user.user_id} will open here.`);
            });

            userAccessContainer.appendChild(div);
        });
        lucide.createIcons();
    }

    // 3. Modal Interactions
    addOrgBtn.addEventListener('click', () => {
        orgModal.classList.remove('hidden');
        orgModal.classList.add('flex');
    });

    closeModal.addEventListener('click', () => {
        orgModal.classList.add('hidden');
        orgModal.classList.remove('flex');
        orgForm.reset();
    });

    // Close on outside click
    orgModal.addEventListener('click', (e) => {
        if (e.target === orgModal) {
            closeModal.click();
        }
    });

    // 4. Create Organization Submission
    orgForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const orgName = document.getElementById('new-org-name').value;
        const orgTier = document.getElementById('new-org-tier').value;
        const submitBtn = orgForm.querySelector('button[type="submit"]');

        if (!orgName) return;

        submitBtn.disabled = true;
        submitBtn.textContent = 'INITIALIZING...';

        try {
            const response = await fetch('/api/admin/organizations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: orgName,
                    subscription_tier: orgTier
                })
            });

            const result = await response.json();
            if (response.ok && result.status === 'SUCCESS') {
                submitBtn.classList.replace('bg-amber-400', 'bg-green-500');
                submitBtn.textContent = 'SUCCESS';
                
                setTimeout(() => {
                    closeModal.click();
                    submitBtn.classList.replace('bg-green-500', 'bg-amber-400');
                    submitBtn.textContent = 'INITIALIZE';
                    submitBtn.disabled = false;
                    fetchSystemData(); // Refresh list
                }, 1000);
            } else {
                throw new Error(result.detail || 'Failed to create organization');
            }
        } catch (error) {
            console.error(error);
            submitBtn.textContent = 'ERROR - RETRY';
            submitBtn.disabled = false;
        }
    });

    // Initialize
    fetchSystemData();
});

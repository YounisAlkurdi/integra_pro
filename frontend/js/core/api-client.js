/**
 * 🛰️ INTEGRA API CLIENT
 * Centralized fetch wrapper for all backend communication.
 * Handles authentication headers and error normalization.
 */

// We import from window.supabase if already initialized by a script tag, 
// or wait for the module if needed.
const getSupabase = async () => {
    if (window.supabase) return window.supabase;
    // Fallback to import if window object isn't ready
    const { supabase } = await import('./supabase-client.js');
    return supabase;
};

export const apiClient = {
    async request(path, options = {}) {
        const baseUrl = window.APP_CONFIG?.backendUrl || 'http://127.0.0.1:8000';
        const url = `${baseUrl}${path}`;

        // Get active session for Bearer token
        const supabase = await getSupabase();
        const { data: { session } } = await supabase.auth.getSession();
        
        const headers = {
            'Content-Type': 'application/json',
            ...(session?.access_token && { 'Authorization': `Bearer ${session.access_token}` }),
            ...options.headers
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(data.detail || `Request failed with status ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error(`=> API Error [${path}]:`, error);
            throw error;
        }
    },

    get(path, options = {}) {
        return this.request(path, { ...options, method: 'GET' });
    },

    post(path, body, options = {}) {
        return this.request(path, { 
            ...options, 
            method: 'POST', 
            body: body ? JSON.stringify(body) : undefined
        });
    },

    put(path, body, options = {}) {
        return this.request(path, { 
            ...options, 
            method: 'PUT', 
            body: body ? JSON.stringify(body) : undefined
        });
    },

    delete(path, options = {}) {
        return this.request(path, { ...options, method: 'DELETE' });
    }
};

// Expose globally for legacy scripts
window.apiClient = apiClient;

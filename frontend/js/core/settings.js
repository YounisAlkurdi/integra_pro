/**
 * Integra Unified Settings & Core Bridge
 * Centralized configuration and high-performance API wrapper.
 */
window.INTEGRA_CORE = {
    // Endpoints
    API_BASE: (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') 
        ? `${window.location.protocol}//${window.location.hostname}:8000` 
        : '',
    
    // Internal Cache
    _cache: new Map(),

    /**
     * Authenticated Request Wrapper
     */
    async request(path, options = {}) {
        let token = localStorage.getItem('integra_token');
        
        // Try to get token from Supabase session if window.supabase is available
        if (!token && window.supabase) {
            const { data: { session } } = await window.supabase.auth.getSession();
            if (session) token = session.access_token;
        }

        if (!token && !path.includes('/auth') && !path.includes('/init') && !path.includes('/health')) {
            // Only redirect if we're not already on login/index
            if (!['/', '/login', '/index.html'].includes(window.location.pathname)) {
                window.location.href = '/login';
                return;
            }
        }

        const url = path.startsWith('http') ? path : `${this.API_BASE}${path}`;
        
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers: { ...defaultHeaders, ...options.headers }
            });

            if (response.status === 401 && !path.includes('/auth')) {
                localStorage.removeItem('integra_token');
                window.location.href = '/login';
                return;
            }

            return await response.json();
        } catch (error) {
            console.error(`[API Error] ${path}:`, error);
            if (window.showToast) window.showToast("Connection to Core Interrupted", "error");
            throw error;
        }
    }
};

window.INTEGRA_SETTINGS = {
    BASE_URL: window.INTEGRA_CORE.API_BASE,
    SUPABASE_URL: 'https://ljnclcivnbhjjofsfyzm.supabase.co',
    SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxqbmNsY2l2bmJoampvZnNmeXptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU1ODY5NjAsImV4cCI6MjA5MTE2Mjk2MH0.QveyJDvJuOeNPJHFwYZx-XD_UeJ5SqsDRdUPI61CbDk',
    LIVEKIT_URL: 'wss://youness-elysip4f.livekit.cloud',
    STT_LANG: 'ar-SA',
    endpoint: (path) => `${window.INTEGRA_CORE.API_BASE}${path}`
};

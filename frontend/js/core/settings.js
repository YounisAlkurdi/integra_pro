/**
 * Integra Unified Settings
 * Centralized configuration for all API endpoints and third-party keys.
 */
window.INTEGRA_SETTINGS = {
    // ☁️ AWS Production Backend (DuckDNS)
    AWS_DOMAIN: 'integra-ai.duckdns.org',

    // Current Active Backend Base — Routes to AWS in production, localhost in dev
    get BASE_URL() {
        const isLocal = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost';
        return isLocal ? 'http://localhost:8000' : `https://${this.AWS_DOMAIN}`;
    },

    // Fallback list for local testing
    API_FALLBACK_URLS: [
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],

    // Supabase Configuration
    SUPABASE_URL: 'https://ljnclcivnbhjjofsfyzm.supabase.co',
    SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxqbmNsY2l2bmJoampvZnNmeXptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU1ODY5NjAsImV4cCI6MjA5MTE2Mjk2MH0.QveyJDvJuOeNPJHFwYZx-XD_UeJ5SqsDRdUPI61CbDk',

    // Helper to get formatted endpoint
    endpoint: function(path) {
        return `${this.BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
    }
};

// Global Supabase Initialization
if (typeof supabase !== 'undefined') {
    window.supabaseClient = supabase.createClient(
        window.INTEGRA_SETTINGS.SUPABASE_URL,
        window.INTEGRA_SETTINGS.SUPABASE_ANON_KEY
    );
}

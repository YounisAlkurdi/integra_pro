/**
 * Integra Unified Settings
 * Centralized configuration for all API endpoints and third-party keys.
 */
window.INTEGRA_SETTINGS = {
    // Current Active Backend Base
    BASE_URL: window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' 
              ? 'http://localhost:8000' 
              : window.location.origin,
    
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

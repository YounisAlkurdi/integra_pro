/**
 * 🌎 INTEGRA CENTRAL CONFIGURATION
 * This file handles dynamic switching between Localhost and AWS Production.
 */

window.APP_CONFIG = {
    // ☁️ AWS PRODUCTION IP (Update this once your AWS server is live)
    awsIp: '3.123.45.67', 

    // 🤖 BACKEND URL (Dynamic Detection)
    get backendUrl() {
        const isLocal = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost';
        return isLocal ? 'http://127.0.0.1:8000' : `http://${this.awsIp}:8000`;
    },

    // 📡 WEBSOCKET URL (Dynamic Detection)
    get wsUrl() {
        const isLocal = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost';
        // Note: ws:// for local, wss:// if you add SSL to AWS later
        return isLocal ? `ws://127.0.0.1:8000/ws/behavioral` : `ws://${this.awsIp}:8000/ws/behavioral`;
    },

    // 📊 NLP API PATH
    get nlpUrl() {
        return this.backendUrl + '/api';
    },

    // 🗄️ Supabase
    supabaseUrl:  'https://ljnclcivnbhjjofsfyzm.supabase.co',
    supabaseAnon: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxqbmNsY2l2bmJoampvZnNmeXptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU1ODY5NjAsImV4cCI6MjA5MTE2Mjk2MH0.QveyJDvJuOeNPJHFwYZx-XD_UeJ5SqsDRdUPI61CbDk',

    // 🎥 LiveKit
    livekitUrl: 'wss://youness-elysip4f.livekit.cloud',

    // 🗣️ STT default language
    sttLang: 'ar-SA'
};

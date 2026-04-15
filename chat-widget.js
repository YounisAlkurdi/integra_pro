/**
 * Chat Widget JS — Integra AI Agent
 * Connects the dashboard UI widget to the FastAPI /api/agent/chat endpoint.
 */

import { supabase } from './supabase-client.js';

document.addEventListener("DOMContentLoaded", () => {
    // Check if widget exists
    const chatBtn = document.getElementById("ai-chat-btn");
    const chatBox = document.getElementById("ai-chat-window");
    const chatClose = document.getElementById("ai-chat-close");
    const chatInput = document.getElementById("ai-chat-input");
    const chatSend = document.getElementById("ai-chat-send");
    const chatContainer = document.getElementById("ai-chat-messages");

    if (!chatBtn || !chatBox) return;

    // Toggle Chat
    chatBtn.addEventListener("click", () => {
        chatBox.classList.toggle("hidden");
        chatBox.classList.toggle("opacity-0");
        chatBox.classList.toggle("translate-y-10");
        if (!chatBox.classList.contains("hidden")) {
            chatInput.focus();
        }
    });

    chatClose.addEventListener("click", () => {
        chatBox.classList.add("opacity-0", "translate-y-10");
        setTimeout(() => chatBox.classList.add("hidden"), 300);
    });

    // Send Message
    const sendMessage = async () => {
        const text = chatInput.value.trim();
        if (!text) return;

        // Add user message to UI
        appendMessage(text, "user");
        chatInput.value = "";

        // Add thinking indicator
        const typingId = appendMessage("...", "ai", true);

        try {
            // Get user session token
            const { data: { session } } = await supabase.auth.getSession();
            const token = session?.access_token;

            if (!token) {
                document.getElementById(typingId)?.remove();
                appendMessage("[Error] Identity Signal Missing. Please log in again.", "error");
                return;
            }

            // Load config from settings page local storage
            let llmConfig = {};
            try {
                llmConfig = JSON.parse(localStorage.getItem("INTEGRA_LLM_CONFIG") || "{}");
            } catch (e) {
                console.warn("Failed to load LLM config, using defaults");
            }

            // Get endpoint securely using BASE_URL
            const endpoint = window.INTEGRA_SETTINGS?.BASE_URL 
                ? `${window.INTEGRA_SETTINGS.BASE_URL}/api/agent/chat`
                : '/api/agent/chat';

            const response = await fetch(endpoint, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    prompt: text,
                    config: llmConfig
                })
            });

            const data = await response.json();
            
            // Remove typing indicator
            document.getElementById(typingId)?.remove();

            if (response.ok && data.response) {
                appendMessage(data.response, "ai");
            } else {
                appendMessage(`[Error] ${data.detail || "Connection Failed"}`, "error");
            }
        } catch (error) {
            document.getElementById(typingId)?.remove();
            appendMessage(`[System Error] ${error.message}`, "error");
        }
    };

    chatSend.addEventListener("click", sendMessage);
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Helper: Add message to box
    function appendMessage(text, sender, isTyping = false) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `p-3 rounded-2xl text-[11px] font-mono leading-relaxed max-w-[85%] ${
            sender === "user" 
                ? "bg-cyan-400 text-obsidian self-end rounded-br-none" 
                : sender === "error"
                    ? "bg-red-500/20 text-red-400 border border-red-500/30 self-start rounded-bl-none"
                    : "bg-white/5 border border-white/10 text-white/80 self-start rounded-bl-none"
        }`;
        
        if (isTyping) {
            msgDiv.classList.add("animate-pulse");
            msgDiv.id = "typing-" + Date.now();
        }
        
        // Basic Markdown formatting for AI (convert newlines to br, asterisks to bold)
        if (sender === "ai") {
            let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            formatted = formatted.replace(/\n/g, '<br>');
            msgDiv.innerHTML = formatted;
        } else {
            msgDiv.textContent = text;
        }

        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return msgDiv.id;
    }
});

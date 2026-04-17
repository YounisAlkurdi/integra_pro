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
        
        // Basic Markdown formatting for AI
        if (sender === "ai") {
            let formatted = text;
            
            // Render INTEGRA_UI_CARD payloads
            const cardRegex = /\[INTEGRA_UI_CARD:\s*(\{[\s\S]*?\})\s*\]/g;
            let match;
            while ((match = cardRegex.exec(text)) !== null) {
                try {
                    const payload = JSON.parse(match[1]);
                    let cardHtml = "";
                    if (payload.type === 'link') {
                        cardHtml = `
                            <div class="mt-3 p-4 bg-white/[0.03] border border-cyan-500/20 rounded-xl backdrop-blur-md shadow-lg shadow-black/20">
                                <div class="flex items-center gap-2 mb-2">
                                    <svg class="w-4 h-4 text-cyan-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
                                    <a href="${payload.url}" target="_blank" class="text-cyan-400 font-semibold hover:text-cyan-300 hover:underline truncate block w-full transition-colors">${payload.title}</a>
                                </div>
                                <p class="text-white/60 text-xs leading-relaxed line-clamp-3">${payload.summary}</p>
                            </div>
                        `;
                    } else if (payload.type === 'image') {
                         const techSpecs = Object.entries(payload.tech_data || {}).map(([k,v]) => `<span class="bg-black/50 px-2 py-1 rounded text-[10px] text-cyan-200 capitalize font-medium">${k}: ${v}</span>`).join('');
                         cardHtml = `
                            <div class="mt-3 border border-white/10 rounded-xl overflow-hidden bg-black/40 shadow-lg shadow-black/20">
                                <a href="${payload.path}" target="_blank" class="block relative group flex justify-center bg-black/60">
                                    <img src="${payload.path}" class="w-full max-h-48 object-contain opacity-90 group-hover:opacity-100 transition duration-300" />
                                    <div class="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition duration-300">
                                        <svg class="w-8 h-8 text-white drop-shadow-md" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                                    </div>
                                </a>
                                <div class="p-3 flex gap-2 flex-wrap border-t border-white/10 bg-white/[0.02]">
                                    ${techSpecs}
                                </div>
                            </div>
                         `;
                    } else if (payload.type === 'file') {
                         const safeId = "code-" + Date.now() + Math.floor(Math.random()*100);
                         const filename = payload.filepath.split('/').pop().split('\\').pop();
                         cardHtml = `
                            <div class="mt-3 border border-white/10 rounded-xl overflow-hidden bg-[#0d1117] shadow-lg shadow-black/20">
                                <div class="flex justify-between items-center px-4 py-2 bg-white/[0.03] border-b border-white/10">
                                    <span class="text-xs text-white/60 font-mono flex items-center gap-2 font-medium">
                                        <svg class="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                                        ${filename}
                                    </span>
                                    <button onclick="navigator.clipboard.writeText(document.getElementById('${safeId}').innerText); this.innerText='Copied!'; setTimeout(()=>this.innerText='Copy', 2000)" class="text-[10px] bg-white/5 hover:bg-white/10 text-white/80 border border-white/10 px-3 py-1 rounded-md transition-all font-medium">Copy</button>
                                </div>
                                <div class="p-4 overflow-x-auto max-h-60 overflow-y-auto custom-scrollbar">
                                    <pre id="${safeId}" class="text-[11px] text-gray-300 font-mono m-0 leading-relaxed">${payload.content.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>
                                </div>
                            </div>
                         `;
                    }
                    formatted = formatted.replace(match[0], cardHtml);
                } catch(e) {
                    console.error("Failed to parse INTEGRA_UI_CARD", e);
                }
            }

            // Render INTEGRA_SYSTEM_EVENT signals (Invisible to user, but triggers UI updates)
            const eventRegex = /\[INTEGRA_SYSTEM_EVENT:\s*(\{[\s\S]*?\})\s*\]/g;
            let eventMatch;
            while ((eventMatch = eventRegex.exec(text)) !== null) {
                try {
                    const eventData = JSON.parse(eventMatch[1]);
                    console.log("Integra System Event Received:", eventData);
                    window.dispatchEvent(new CustomEvent('integra-system-event', { detail: eventData }));
                    // Remove the marker from the text so the user doesn't see it
                    formatted = formatted.replace(eventMatch[0], "");
                } catch(e) {
                    console.error("Failed to parse INTEGRA_SYSTEM_EVENT", e);
                }
            }
            
            // Standard formatting
            formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
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

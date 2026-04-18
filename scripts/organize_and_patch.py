import os
import shutil
import subprocess
import re

ROOT_DIR = r"C:\tist_integra"
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

MOVES = {
    "agent_routes.py": os.path.join(BACKEND_DIR, "agent_routes.py"),
    "agent_tools.py": os.path.join(BACKEND_DIR, "agent_tools.py"),
    "api_bridge.py": os.path.join(BACKEND_DIR, "api_bridge.py"),
    "integra_mcp.py": os.path.join(BACKEND_DIR, "integra_mcp.py"),
    "nodes.py": os.path.join(BACKEND_DIR, "nodes.py"),
    "llm": os.path.join(BACKEND_DIR, "llm"),
    "llm-config.html": os.path.join(FRONTEND_DIR, "pages", "llm-config.html"),
    "llm-config.js": os.path.join(FRONTEND_DIR, "js", "pages", "llm-config.js"),
    "models.config.js": os.path.join(FRONTEND_DIR, "js", "core", "models.config.js"),
}

os.makedirs(os.path.join(FRONTEND_DIR, "js", "components"), exist_ok=True)
MOVES["chat-widget.js"] = os.path.join(FRONTEND_DIR, "js", "components", "chat-widget.js")

print("1. Moving files to correct folders...")
for src_name, dst_path in MOVES.items():
    src_path = os.path.join(ROOT_DIR, src_name)
    if os.path.exists(src_path):
        if os.path.exists(dst_path):
            if os.path.isdir(dst_path):
                shutil.rmtree(dst_path)
            else:
                os.remove(dst_path)
        shutil.move(src_path, dst_path)
        print(f"Moved: {src_name} -> {dst_path}")

chat_widget_path = MOVES["chat-widget.js"]
if os.path.exists(chat_widget_path):
    with open(chat_widget_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("from './supabase-client.js';", "from '../core/supabase-client.js';")
    with open(chat_widget_path, "w", encoding="utf-8") as f:
        f.write(content)

print("\n2. Patching dashboard.html with Chat Widget...")
dashboard_path = os.path.join(FRONTEND_DIR, "pages", "dashboard.html")
if os.path.exists(dashboard_path):
    with open(dashboard_path, "r", encoding="utf-8") as f:
        dash_content = f.read()
    if "ai-chat-btn" not in dash_content:
        chat_html = """
    <!-- AI Chat Widget -->
    <button id="ai-chat-btn" class="fixed bottom-6 right-6 w-14 h-14 bg-cyan-500 rounded-full flex items-center justify-center shadow-lg hover:bg-cyan-400 transition z-50">
        <i data-lucide="message-square" class="text-obsidian w-6 h-6"></i>
    </button>
    <div id="ai-chat-window" class="fixed bottom-24 right-6 w-96 h-[30rem] bg-obsidian border border-white/10 rounded-2xl shadow-2xl flex flex-col hidden opacity-0 translate-y-10 transition-all z-50 overflow-hidden">
        <div class="p-4 bg-white/5 border-b border-white/10 flex justify-between items-center">
            <h3 class="text-xs font-black uppercase tracking-widest text-cyan-400 flex items-center gap-2">
                <i data-lucide="cpu" class="w-4 h-4"></i> Integra Agent
            </h3>
            <button id="ai-chat-close" class="text-white/50 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
        </div>
        <div id="ai-chat-messages" class="flex-1 p-4 overflow-y-auto flex flex-col gap-3 custom-scrollbar">
            <div class="p-3 bg-white/5 rounded-2xl rounded-bl-none text-[11px] font-mono text-white/80 w-fit max-w-[85%] border border-white/10">
                System online. How can I assist you today?
            </div>
        </div>
        <div class="p-4 border-t border-white/10 bg-black/20 flex gap-2">
            <input type="text" id="ai-chat-input" placeholder="Type a command..." class="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white outline-none focus:border-cyan-400/50">
            <button id="ai-chat-send" class="p-2 bg-cyan-500/20 text-cyan-400 rounded-xl hover:bg-cyan-500 hover:text-obsidian border border-cyan-500/30 transition">
                <i data-lucide="send" class="w-4 h-4"></i>
            </button>
        </div>
    </div>
"""
        dash_content = dash_content.replace("</body>", chat_html + "\n    <script type=\"module\" src=\"../js/components/chat-widget.js\"></script>\n</body>")
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(dash_content)

print("\n3. Patching profile.html & profile.js from mcp branch...")
try:
    profile_html_mcp = subprocess.check_output(["git", "show", "mcp:profile.html"], cwd=ROOT_DIR, text=True, encoding="utf-8")
    match = re.search(r'(<!-- NEW: Neural Hub Export Section -->.*?)<div class="mt-12 flex gap-4">', profile_html_mcp, re.DOTALL)
    if match:
        new_sections = match.group(1)
        local_profile_path = os.path.join(FRONTEND_DIR, "pages", "profile.html")
        with open(local_profile_path, "r", encoding="utf-8") as f:
            local_profile = f.read()
        if "<!-- NEW: Neural Hub Export Section -->" not in local_profile:
            local_profile = local_profile.replace('<div class="mt-12 flex gap-4">', new_sections + '\n            <div class="mt-12 flex gap-4">')
            with open(local_profile_path, "w", encoding="utf-8") as f:
                f.write(local_profile)

    profile_js_mcp = subprocess.check_output(["git", "show", "mcp:profile.js"], cwd=ROOT_DIR, text=True, encoding="utf-8")
    js_match = re.search(r'(// \-\-\- MCP Configuration & External Matrix Links \-\-\-.*)', profile_js_mcp, re.DOTALL)
    if js_match:
        new_js = js_match.group(1)
        local_profile_js_path = os.path.join(FRONTEND_DIR, "js", "pages", "profile.js")
        with open(local_profile_js_path, "r", encoding="utf-8") as f:
            local_js = f.read()
        if "loadExternalMCPs" not in local_js:
            with open(local_profile_js_path, "a", encoding="utf-8") as f:
                f.write("\n\n" + new_js)
    print("Patching completed successfully!")
except Exception as e:
    print(f"Warning: {e}")

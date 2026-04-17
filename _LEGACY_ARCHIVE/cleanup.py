import os
import re

root_dir = "c:/tist_integra"

html_files_to_move = {
    "llm-config.html": "frontend/pages",
    "reports.html": "frontend/pages",
    "appointments.html": "frontend/pages",
    "checkout.html": "frontend/pages",
    "integra-session.html": "frontend/pages"
}

js_files_to_move = {
    "appointments.js": "frontend/js/pages",
    "checkout.js": "frontend/js/pages",
    "integra-session.js": "frontend/js/pages",
    "livekit-session.js": "frontend/js/pages",
    "llm-config.js": "frontend/js/pages",
    "reports.js": "frontend/js/pages",
    "chat-widget.js": "frontend/js/pages",
    "stt.js": "frontend/js/core",
    "config.js": "frontend/js/core",
    "models.config.js": "frontend/js/core",
    "script.js": "frontend/js/core",
    "settings.js": "frontend/js/core",
    "supabase-client.js": "frontend/js/core"
}

css_files_to_move = {
    "checkout-card.css": "frontend/css",
    "integra-session.css": "frontend/css",
    "reports.css": "frontend/css",
    "style.css": "frontend/css"
}

files_to_delete = [
    "index.html", "dashboard.html", "dashboard.js", "profile.html", "profile.js",
    "login.html", "login.js", "pricing.html", "pricing.js", "billing.html", "billing.js",
    "agent_routes.py", "agent_tools.py", "api_bridge.py", "auth.py", "integra_mcp.py",
    "livekit_routes.py", "logs.py", "mailer.py", "main.py", "nodes.py", "payments.py",
    "supabase_client.py", "utils.py"
]

def fix_html_paths(content):
    # Fix CSS paths
    content = re.sub(r'href="([^"]*\.css)"', r'href="../css/\1"', content)
    # Fix standard JS paths that belong to core
    core_scripts = ["script.js", "settings.js", "supabase-client.js", "stt.js", "config.js", "models.config.js"]
    for script in core_scripts:
        content = re.sub(rf'src="{script}"', f'src="../js/core/{script}"', content)
    # Fix page-specific JS paths
    page_scripts = ["appointments.js", "checkout.js", "integra-session.js", "livekit-session.js", "llm-config.js", "reports.js", "chat-widget.js", "login.js", "dashboard.js", "pricing.js", "billing.js", "profile.js"]
    for script in page_scripts:
        content = re.sub(rf'src="{script}"', f'src="../js/pages/{script}"', content)
    # Fix HTML links to point to same folder
    # Assuming all html are in same folder now
    return content

print("Starting Deep Cleanup & Migration...")

# Move and fix HTML files
for f, dest in html_files_to_move.items():
    src_path = os.path.join(root_dir, f)
    dest_dir = os.path.join(root_dir, dest)
    dest_path = os.path.join(dest_dir, f)
    
    if os.path.exists(src_path):
        os.makedirs(dest_dir, exist_ok=True)
        with open(src_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        content = fix_html_paths(content)
        
        with open(dest_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        print(f"Moved and updated {f} to {dest}")
        os.remove(src_path)

# Move JS files
for f, dest in js_files_to_move.items():
    src_path = os.path.join(root_dir, f)
    dest_dir = os.path.join(root_dir, dest)
    dest_path = os.path.join(dest_dir, f)
    
    if os.path.exists(src_path):
        os.makedirs(dest_dir, exist_ok=True)
        with open(src_path, 'r', encoding='utf-8') as file:
            content = file.read()
        with open(dest_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Moved {f} to {dest}")
        os.remove(src_path)

# Move CSS files
for f, dest in css_files_to_move.items():
    src_path = os.path.join(root_dir, f)
    dest_dir = os.path.join(root_dir, dest)
    dest_path = os.path.join(dest_dir, f)
    
    if os.path.exists(src_path):
        os.makedirs(dest_dir, exist_ok=True)
        with open(src_path, 'r', encoding='utf-8') as file:
            content = file.read()
        with open(dest_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Moved {f} to {dest}")
        os.remove(src_path)

# Delete known duplicates
for f in files_to_delete:
    src_path = os.path.join(root_dir, f)
    if os.path.exists(src_path):
        os.remove(src_path)
        print(f"Deleted duplicate file: {f}")

print("Cleanup complete. All files moved and paths fixed.")

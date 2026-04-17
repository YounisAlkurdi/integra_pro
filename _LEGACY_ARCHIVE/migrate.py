import os
import shutil

# 1. Create Directories
dirs = [
    "backend", "backend/routes", 
    "frontend", "frontend/pages", "frontend/js", "frontend/js/core", "frontend/js/pages", "frontend/js/utils", "frontend/css",
    "assets", "assets/images", "assets/video", "assets/design", "assets/frames",
    "data"
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
    print(f"Created directory: {d}")

# 2. Define File Movements
move_map = {
    # Backend
    "backend": [
        "main.py", "auth.py", "nodes.py", "payments.py", "livekit_routes.py", 
        "logs.py", "utils.py", "requirements.txt", "supabase_client.py", 
        "agent_routes.py", "agent_tools.py", "api_bridge.py", "integra_mcp.py", "mailer.py"
    ],
    # Frontend Pages
    "frontend/pages": [
        "index.html", "login.html", "dashboard.html", "appointments.html", 
        "reports.html", "pricing.html", "checkout.html", "integra-session.html",
        "profile.html", "billing.html", "llm-config.html"
    ],
    # Frontend JS Core
    "frontend/js/core": [
        "settings.js", "supabase-client.js", "stt.js", "config.js", "models.config.js"
    ],
    # Frontend JS Pages
    "frontend/js/pages": [
        "login.js", "dashboard.js", "appointments.js", "reports.js", "pricing.js", 
        "checkout.js", "integra-session.js", "livekit-session.js", "script.js",
        "profile.js", "billing.js", "llm-config.js", "chat-widget.js"
    ],
    # Frontend CSS
    "frontend/css": [
        "style.css", "checkout-card.css", "integra-session.css", "reports.css"
    ],
    # Data
    "data": [
        "pricing.json"
    ]
}

# 3. Move Files
for target_dir, files in move_map.items():
    for f in files:
        if os.path.exists(f):
            try:
                # Use shutil.move for reliable moving across file systems if needed
                shutil.move(f, os.path.join(target_dir, f))
                print(f"Moved {f} -> {target_dir}")
            except Exception as e:
                print(f"Error moving {f}: {e}")

# 4. Move Assets Folders
assets_map = {
    "Images": "assets/images",
    "video": "assets/video",
    "Design": "assets/design",
    "frames": "assets/frames"
}

for src, dst in assets_map.items():
    if os.path.exists(src) and os.path.isdir(src):
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            try:
                shutil.move(s, d)
                print(f"Moved asset {s} -> {dst}")
            except Exception as e:
                print(f"Error moving asset {s}: {e}")
        # Remove empty src dir if all moved
        try:
            os.rmdir(src)
            print(f"Removed source directory: {src}")
        except:
            pass

print("\n--- Migration Complete ---")

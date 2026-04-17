import os
import shutil

# Define source and destination mappings
migration_map = {
    # Pages JS
    "appointments.js": "frontend/js/pages/appointments.js",
    "checkout.js": "frontend/js/pages/checkout.js",
    "integra-session.js": "frontend/js/pages/integra-session.js",
    "llm-config.js": "frontend/js/pages/llm-config.js",
    "billing.js": "frontend/js/pages/billing.js",
    "dashboard.js": "frontend/js/pages/dashboard.js",
    "login.js": "frontend/js/pages/login.js",
    "pricing.js": "frontend/js/pages/pricing.js",
    "profile.js": "frontend/js/pages/profile.js",
    "reports.js": "frontend/js/pages/reports.js",
    "script.js": "frontend/js/pages/script.js",
    
    # Core JS
    "models.config.js": "frontend/js/core/models.config.js",
    "stt.js": "frontend/js/core/stt.js",
    "settings.js": "frontend/js/core/settings.js",
    "config.js": "frontend/js/core/config.js",
    "supabase-client.js": "frontend/js/core/supabase-client.js",
    "livekit-session.js": "frontend/js/core/livekit-session.js",
    "chat-widget.js": "frontend/js/core/chat-widget.js",
    
    # CSS
    "checkout-card.css": "frontend/css/checkout-card.css",
    "integra-session.css": "frontend/css/integra-session.css",
    "reports.css": "frontend/css/reports.css",
    "style.css": "frontend/css/style.css",
    
    # Assets
    "Images/cv.png": "frontend/assets/images/cv.png"
}

def migrate():
    for src, dst in migration_map.items():
        if os.path.exists(src):
            # Create destination directory if it doesn't exist
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            
            # Check if destination exists and if source is newer
            if os.path.exists(dst):
                src_time = os.path.getmtime(src)
                dst_time = os.path.getmtime(dst)
                if src_time > dst_time:
                    print(f"Updating {dst} (Source is newer)")
                    shutil.copy2(src, dst)
                else:
                    print(f"Skipping {dst} (Destination is newer or same)")
            else:
                print(f"Copying {src} to {dst}")
                shutil.copy2(src, dst)
        else:
            print(f"Source {src} not found")

if __name__ == "__main__":
    migrate()

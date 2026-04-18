import os
import re

FRONTEND_PAGES_DIR = "frontend/pages"
FRONTEND_JS_PAGES_DIR = "frontend/js/pages"

def replace_in_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)
        
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ Updated: {filepath}")

# 1. تحديث مسارات ملفات HTML
html_replacements = {
    # CSS
    'href="style.css"': 'href="../css/style.css"',
    'href="checkout-card.css"': 'href="../css/checkout-card.css"',
    'href="integra-session.css"': 'href="../css/integra-session.css"',
    'href="reports.css"': 'href="../css/reports.css"',
    
    # Core JS
    'src="settings.js"': 'src="../js/core/settings.js"',
    'src="supabase-client.js"': 'src="../js/core/supabase-client.js"',
    'src="stt.js"': 'src="../js/core/stt.js"',
    'src="config.js"': 'src="../js/core/config.js"',
    
    # Pages JS
    'src="script.js"': 'src="../js/pages/script.js"',
    'src="login.js"': 'src="../js/pages/login.js"',
    'src="dashboard.js"': 'src="../js/pages/dashboard.js"',
    'src="appointments.js?v=6"': 'src="../js/pages/appointments.js?v=6"',
    'src="reports.js"': 'src="../js/pages/reports.js"',
    'src="pricing.js"': 'src="../js/pages/pricing.js"',
    'src="checkout.js"': 'src="../js/pages/checkout.js"',
    'src="integra-session.js"': 'src="../js/pages/integra-session.js"',
    'src="livekit-session.js"': 'src="../js/pages/livekit-session.js"',
    'src="profile.js"': 'src="../js/pages/profile.js"',
    'src="billing.js"': 'src="../js/pages/billing.js"',
    
    # Assets (صور وتصميم)
    'src="images/': 'src="../../assets/images/',
    'src="video/': 'src="../../assets/video/',
    'src="Design/': 'src="../../assets/design/',
    'src="frames/': 'src="../../assets/frames/',
}

print("🔄 Starting HTML path updates...")
for filename in os.listdir(FRONTEND_PAGES_DIR):
    if filename.endswith('.html'):
        filepath = os.path.join(FRONTEND_PAGES_DIR, filename)
        replace_in_file(filepath, html_replacements)

# 2. تحديث المسارات داخل ملفات الـ JavaScript
js_replacements = {
    "fetch('pricing.json')": "fetch('../../data/pricing.json')"
}

print("🔄 Starting JavaScript path updates...")
for filename in os.listdir(FRONTEND_JS_PAGES_DIR):
    if filename.endswith('.js'):
        filepath = os.path.join(FRONTEND_JS_PAGES_DIR, filename)
        replace_in_file(filepath, js_replacements)

print("🎉 All paths updated successfully!")

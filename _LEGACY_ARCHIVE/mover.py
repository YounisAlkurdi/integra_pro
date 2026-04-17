import os
import shutil

moves = [
    (r"c:\tist_integra\appointments.js", r"c:\tist_integra\frontend\js\pages\appointments.js"),
    (r"c:\tist_integra\checkout.js", r"c:\tist_integra\frontend\js\pages\checkout.js"),
    (r"c:\tist_integra\reports.js", r"c:\tist_integra\frontend\js\pages\reports.js"),
    (r"c:\tist_integra\llm-config.js", r"c:\tist_integra\frontend\js\pages\llm-config.js"),
    (r"c:\tist_integra\integra-session.js", r"c:\tist_integra\frontend\js\pages\integra-session.js"),
    (r"c:\tist_integra\livekit-session.js", r"c:\tist_integra\frontend\js\core\livekit-session.js"),
    (r"c:\tist_integra\models.config.js", r"c:\tist_integra\frontend\js\core\models.config.js"),
    (r"c:\tist_integra\stt.js", r"c:\tist_integra\frontend\js\core\stt.js"),
    (r"c:\tist_integra\config.js", r"c:\tist_integra\frontend\js\core\config.js"),
]

for src, dst in moves:
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        print(f"Moved {src} to {dst}")

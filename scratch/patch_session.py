"""Patch integra-session.js - fix session lifecycle bugs"""
import re

path = r"c:\tist_integra\frontend\js\pages\integra-session.js"

# Read as bytes then decode with latin-1 to preserve all characters exactly
with open(path, "rb") as f:
    raw = f.read()

src = raw.decode("utf-8", errors="replace")

patches_applied = 0

# ── PATCH 1: lk:reconnected handler ──────────────────────────────────────────
# Find it by the unique surrounding context
if "lk:reconnected" in src:
    # Replace from lk:reconnected event start to its closing });
    pat1 = re.compile(
        r"(window\.addEventListener\('lk:reconnected',\s*\(\)\s*=>\s*\{)[^}]+\}\);",
        re.DOTALL
    )
    repl1 = r"""\1
        if (disconnectGraceTimer) { clearTimeout(disconnectGraceTimer); disconnectGraceTimer = null; }
        if (connectionBadge) {
            connectionBadge.textContent = 'LIVE';
            connectionBadge.className = 'text-[9px] font-mono px-3 py-1 rounded-full bg-cyan-400/10 border border-cyan-400/30 text-cyan-400 uppercase tracking-widest animate-pulse';
        }
        addLog('Reconnected successfully', 'audio');
        showToast('Reconnected!', 'success');
        if (currentRoomId) {
            fetchRoomMeta(currentRoomId).then(meta => {
                if (meta.started_at) {
                    const elapsed   = Math.floor((Date.now() - new Date(meta.started_at).getTime()) / 1000);
                    const remaining = ((meta.max_duration_mins || 10) * 60) - elapsed;
                    if (remaining > 0) startTimer(remaining);
                }
            });
        }
    });"""
    new_src = pat1.sub(repl1, src, count=1)
    if new_src != src:
        src = new_src
        patches_applied += 1
        print("PATCH 1 OK: lk:reconnected fixed")
    else:
        print("PATCH 1 FAIL: lk:reconnected not matched")
else:
    print("PATCH 1 SKIP: lk:reconnected not found in file")

# ── PATCH 2: lk:disconnected handler ─────────────────────────────────────────
if "lk:disconnected" in src:
    pat2 = re.compile(
        r"window\.addEventListener\('lk:disconnected',\s*\(\)\s*=>\s*\{.*?Session terminated by server.*?2000\);\s*\}\s*\}\);",
        re.DOTALL
    )
    repl2 = """window.addEventListener('lk:disconnected', () => {
        clearInterval(timerInterval);
        timerInterval = null;
        if (connectionBadge) {
            connectionBadge.textContent = 'OFFLINE';
            connectionBadge.className = 'text-[9px] font-mono px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/30 uppercase tracking-widest';
        }
        setFeedStatus('hr', 'OFFLINE', false);
        setFeedStatus('candidate', 'OFFLINE', false);
        addLog('Connection closed by server.', 'error');
        if (localRole === 'candidate') {
            showToast('Connection interrupted — waiting for host...', 'error');
            addLog('Waiting 10s for host to reconnect...', 'system');
            disconnectGraceTimer = setTimeout(() => {
                const lkState = window.LiveKitSession?.getState?.();
                if (!lkState || lkState.connectionState !== 'Connected') {
                    window.showTerminationOverlay();
                }
            }, 10000);
        } else {
            if (!sessionEnding) {
                showToast('Session ended', 'error');
                setTimeout(() => { window.location.href = 'dashboard.html'; }, 2000);
            }
        }
    });"""
    new_src = pat2.sub(repl2, src, count=1)
    if new_src != src:
        src = new_src
        patches_applied += 1
        print("PATCH 2 OK: lk:disconnected fixed")
    else:
        print("PATCH 2 FAIL: lk:disconnected not matched")
else:
    print("PATCH 2 SKIP: lk:disconnected not found in file")

# ── PATCH 3: endSession double-call guard ─────────────────────────────────────
if "window.endSession = async function()" in src:
    pat3 = re.compile(
        r"(window\.endSession\s*=\s*async\s*function\s*\(\)\s*\{)\s*showToast\(\"TERMINATING SESSION\.\.\.\",\s*\"info\"\);",
        re.DOTALL
    )
    repl3 = r"""\1
        if (sessionEnding) return;
        sessionEnding = true;
        if (disconnectGraceTimer) { clearTimeout(disconnectGraceTimer); disconnectGraceTimer = null; }
        clearInterval(timerInterval); timerInterval = null;
        showToast("TERMINATING SESSION...", "info");
        addLog('Session termination initiated.', 'error');"""
    new_src = pat3.sub(repl3, src, count=1)
    if new_src != src:
        src = new_src
        patches_applied += 1
        print("PATCH 3 OK: endSession guard inserted")
    else:
        print("PATCH 3 FAIL: endSession not matched")
else:
    print("PATCH 3 SKIP: endSession not found in file")

# ── Write back ────────────────────────────────────────────────────────────────
with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\nDone. {patches_applied}/3 patches applied. Total lines: {src.count(chr(10))}")

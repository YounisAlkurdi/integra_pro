/**
 * livekit-session.js — LiveKit Client Integration v3
 *
 * Fixes vs v2:
 *  - STT interim transcriptions are NO LONGER broadcast over the network
 *    (only final results are sent — prevents data channel flooding)
 *  - Audio elements tracked in a container div (not document.body) and
 *    fully cleaned up on disconnect to prevent ghost audio / memory leak
 *  - Simulcast enabled (L1T3 / L2T3) — reduces bandwidth for 3+ participants
 *  - Reconnection logic: auto-retries on transient disconnect with exponential
 *    backoff (up to 5 attempts before giving up)
 *  - Proper publish options for mic (Krisp-compatible noise suppression settings)
 *
 * DOM Events fired on window:
 *   'lk:connected'            → { room, roomName, participantName, role }
 *   'lk:reconnecting'         → { attempt }
 *   'lk:reconnected'          → {}
 *   'lk:disconnected'         → {}
 *   'lk:participant-joined'   → { identity, name, role }
 *   'lk:participant-left'     → { identity, name }
 *   'lk:participant-video'    → { identity, name, role, element, action: 'add'|'remove' }
 *   'lk:speaking-changed'     → { speakers: [identity, ...] }
 *   'lk:transcription'        → { identity, name, role, text, isFinal }
 *   'lk:mic-toggled'          → { enabled }
 *   'lk:cam-toggled'          → { enabled }
 *   'lk:error'                → { message }
 */

const LiveKitSession = (() => {

    // ── Config ───────────────────────────────────────────────────────────────
    const BACKEND_URL       = window.APP_CONFIG?.backendUrl || 'http://127.0.0.1:8000';
    const MAX_RECONNECTS    = 5;
    const RECONNECT_BASE_MS = 1000; // 1s, 2s, 4s, 8s, 16s

    // ── State ────────────────────────────────────────────────────────────────
    let room          = null;
    let localIdentity = null;
    let localName     = null;
    let localRole     = null;
    let isConnected   = false;
    let reconnectCount = 0;
    let reconnectTimer = null;

    // Track all remote participants { identity → { name, role, videoEl, audioEl } }
    const participants = new Map();

    // Dedicated invisible container for remote audio (never shown, always in DOM)
    let audioContainer = null;
    function getAudioContainer() {
        if (!audioContainer) {
            audioContainer = document.createElement('div');
            audioContainer.id = 'lk-audio-container';
            audioContainer.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;pointer-events:none;';
            document.body.appendChild(audioContainer);
        }
        return audioContainer;
    }

    // ── Helpers ──────────────────────────────────────────────────────────────
    function dispatch(name, detail = {}) {
        window.dispatchEvent(new CustomEvent(name, { detail }));
    }

    function getRoleFromMetadata(metadata) {
        try { return JSON.parse(metadata || '{}').role || 'unknown'; }
        catch { return 'unknown'; }
    }

    // ── Token ────────────────────────────────────────────────────────────────
    async function fetchToken(roomName, participantName, role) {
        const res = await fetch(`${BACKEND_URL}/api/livekit/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ roomName, participantName, role }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
            const msg = err.detail || `HTTP ${res.status}`;
            const error = new Error(msg);
            error.status = res.status; // Attach status code
            throw error;
        }

        return await res.json();
    }

    // ── Per-participant media element management ─────────────────────────────
    function createVideoElement(identity) {
        const el = document.createElement('video');
        el.id = `remote-video-${identity}`;
        el.autoplay = true;
        el.playsInline = true;
        el.muted = false;
        el.className = 'w-full h-full object-cover';
        return el;
    }

    function createAudioElement(identity) {
        const el = document.createElement('audio');
        el.id = `remote-audio-${identity}`;
        el.autoplay = true;
        getAudioContainer().appendChild(el);
        return el;
    }

    function getOrCreateParticipant(identity, name, role) {
        if (!participants.has(identity)) {
            participants.set(identity, { name, role, videoEl: null, audioEl: null });
        }
        const p = participants.get(identity);
        if (name) p.name = name;
        if (role && role !== 'unknown') p.role = role;
        return p;
    }

    /** Clean up all media elements for a participant */
    function cleanupParticipant(identity) {
        const p = participants.get(identity);
        if (!p) return;
        if (p.videoEl) {
            p.videoEl.srcObject = null;
            p.videoEl.remove();
            p.videoEl = null;
        }
        if (p.audioEl) {
            p.audioEl.srcObject = null;
            p.audioEl.remove();
            p.audioEl = null;
        }
        participants.delete(identity);
    }

    /** Clean up ALL participants (on full disconnect) */
    function cleanupAllParticipants() {
        for (const identity of participants.keys()) {
            cleanupParticipant(identity);
        }
        participants.clear();
    }

    // ── Connect ──────────────────────────────────────────────────────────────
    async function connect({ roomName, participantName, role }) {
        if (!window.LivekitClient) {
            dispatch('lk:error', { message: 'LiveKit SDK not loaded.' });
            return;
        }

        const { Room, RoomEvent, Track, ConnectionState, VideoPresets } = window.LivekitClient;

        try {
            // 1. Fetch token (or request join approval)
            const tokenData = await fetchToken(roomName, participantName, role);
            
            // If it's a lobby request, return early so the UI can handle the waiting state
            if (tokenData.status === "AWAITING_APPROVAL") {
                return tokenData;
            }

            localIdentity = participantName;
            localName     = participantName;
            localRole     = role;

            // 2. Create room with simulcast + dynacast
            room = new Room({
                adaptiveStream: true,
                dynacast: true,
                // Simulcast: publish 3 quality layers (low/mid/high) simultaneously
                // so remote subscribers can select quality by bandwidth — reduces lag
                publishDefaults: {
                    simulcast: true,
                    videoSimulcastLayers: [
                        VideoPresets.h180,   // 320×180  ~150kbps  (poor connections)
                        VideoPresets.h360,   // 640×360  ~400kbps  (normal)
                        VideoPresets.h720,   // 1280×720 ~1200kbps (good)
                    ],
                    videoCodec: 'vp8',       // VP8 has best simulcast support
                },
                videoCaptureDefaults: {
                    resolution: { width: 1280, height: 720, frameRate: 30 },
                },
                audioCaptureDefaults: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });

            // 3. Wire events
            room.on(RoomEvent.ConnectionStateChanged, (state) => {
                if (state === ConnectionState.Connected) {
                    isConnected   = true;
                    reconnectCount = 0; // Reset on successful connect

                    // --- Surface any participants already in the room ---
                    room.remoteParticipants.forEach((participant) => {
                        const pRole = getRoleFromMetadata(participant.metadata);
                        const pName = participant.name || participant.identity;
                        getOrCreateParticipant(participant.identity, pName, pRole);
                        dispatch('lk:participant-joined', {
                            identity: participant.identity,
                            name:     pName,
                            role:     pRole,
                        });
                        // Surface any tracks already published
                        participant.trackPublications.forEach((pub) => {
                            if (pub.track && pub.isSubscribed) {
                                const p = getOrCreateParticipant(participant.identity, pName, pRole);
                                if (pub.track.kind === Track.Kind.Video) {
                                    if (!p.videoEl) p.videoEl = createVideoElement(participant.identity);
                                    pub.track.attach(p.videoEl);
                                    dispatch('lk:participant-video', {
                                        identity: participant.identity,
                                        name:     pName,
                                        role:     pRole,
                                        element:  p.videoEl,
                                        action:   'add',
                                    });
                                }
                                if (pub.track.kind === Track.Kind.Audio) {
                                    if (!p.audioEl) p.audioEl = createAudioElement(participant.identity);
                                    pub.track.attach(p.audioEl);
                                }
                            }
                        });
                    });

                    dispatch('lk:connected', { room, roomName, participantName, role });
                }

                if (state === ConnectionState.Disconnected) {
                    isConnected = false;
                    // Attempt auto-reconnect if not a deliberate disconnect
                    if (reconnectCount < MAX_RECONNECTS) {
                        scheduleReconnect(roomName, participantName, role);
                    } else {
                        cleanupAllParticipants();
                        dispatch('lk:disconnected', {});
                        window.STTEngine?.stop();
                    }
                }
            });

            // ── Reconnection events ──────────────────────────────────────────
            room.on(RoomEvent.Reconnecting, () => {
                dispatch('lk:reconnecting', { attempt: reconnectCount + 1 });
            });

            room.on(RoomEvent.Reconnected, () => {
                reconnectCount = 0;
                clearTimeout(reconnectTimer);
                dispatch('lk:reconnected', {});
            });

            // ── Participant events ───────────────────────────────────────────
            room.on(RoomEvent.ParticipantConnected, (participant) => {
                const pRole = getRoleFromMetadata(participant.metadata);
                const pName = participant.name || participant.identity;
                getOrCreateParticipant(participant.identity, pName, pRole);

                dispatch('lk:participant-joined', {
                    identity: participant.identity,
                    name: pName,
                    role: pRole,
                });
            });

            room.on(RoomEvent.ParticipantDisconnected, (participant) => {
                const p = participants.get(participant.identity);
                dispatch('lk:participant-video', {
                    identity: participant.identity,
                    name: p?.name || participant.identity,
                    role: p?.role || 'unknown',
                    element: null,
                    action: 'remove',
                });
                dispatch('lk:participant-left', {
                    identity: participant.identity,
                    name: p?.name || participant.identity,
                });
                // Full cleanup AFTER dispatching remove event
                cleanupParticipant(participant.identity);
            });

            // ── Track events ─────────────────────────────────────────────────
            room.on(RoomEvent.TrackSubscribed, (track, _pub, participant) => {
                const pRole = getRoleFromMetadata(participant.metadata);
                const pName = participant.name || participant.identity;
                const p = getOrCreateParticipant(participant.identity, pName, pRole);

                if (track.kind === Track.Kind.Video) {
                    if (!p.videoEl) p.videoEl = createVideoElement(participant.identity);
                    track.attach(p.videoEl);
                    dispatch('lk:participant-video', {
                        identity: participant.identity,
                        name: pName,
                        role: pRole,
                        element: p.videoEl,
                        action: 'add',
                    });
                }

                if (track.kind === Track.Kind.Audio) {
                    if (!p.audioEl) p.audioEl = createAudioElement(participant.identity);
                    track.attach(p.audioEl);
                }
            });

            room.on(RoomEvent.TrackUnsubscribed, (track, _pub, participant) => {
                const p = participants.get(participant.identity);
                if (track.kind === Track.Kind.Video && p?.videoEl) {
                    track.detach(p.videoEl);
                    dispatch('lk:participant-video', {
                        identity: participant.identity,
                        name: p?.name || participant.identity,
                        role: p?.role || 'unknown',
                        element: p.videoEl,
                        action: 'remove',
                    });
                }
                if (track.kind === Track.Kind.Audio && p?.audioEl) {
                    track.detach(p.audioEl);
                }
            });

            // ── Active speakers ──────────────────────────────────────────────
            room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
                dispatch('lk:speaking-changed', {
                    speakers: speakers.map(s => s.identity),
                });
            });

            // ── Data channel: receive remote STT ─────────────────────────────
            room.on(RoomEvent.DataReceived, (payload, participant) => {
                try {
                    const data = JSON.parse(new TextDecoder().decode(payload));
                    if (data.type === 'transcription') {
                        const p = participants.get(data.identity || participant?.identity);
                        const resolvedRole = p?.role || data.role || 'unknown';

                        dispatch('lk:transcription', {
                            identity: data.identity || participant?.identity,
                            name:     data.name,
                            role:     resolvedRole,
                            text:     data.text,
                            isFinal:  data.isFinal,
                        });
                    }
                } catch (_) {}
            });

            // ── Local track published ────────────────────────────────────────
            room.on(RoomEvent.LocalTrackPublished, (pub) => {
                if (pub.track?.kind === Track.Kind.Video) {
                    dispatch('lk:local-camera', { track: pub.track });
                }
            });

            // 4. Connect
            await room.connect(tokenData.url, tokenData.token);

            // 5. Enable camera & mic
            await room.localParticipant.enableCameraAndMicrophone();

        } catch (err) {
            console.error('[LiveKit] Connection error:', err);
            dispatch('lk:error', { message: err.message });
        }
    }

    // ── Auto-reconnect with exponential backoff ──────────────────────────────
    function scheduleReconnect(roomName, participantName, role) {
        if (!room) return;
        reconnectCount++;
        const delay = Math.min(RECONNECT_BASE_MS * Math.pow(2, reconnectCount - 1), 16000);
        console.warn(`[LiveKit] Reconnect attempt ${reconnectCount}/${MAX_RECONNECTS} in ${delay}ms`);
        dispatch('lk:reconnecting', { attempt: reconnectCount });

        reconnectTimer = setTimeout(async () => {
            try {
                const tokenData = await fetchToken(roomName, participantName, localRole);
                await room.connect(tokenData.url, tokenData.token);
            } catch (err) {
                console.error('[LiveKit] Reconnect failed:', err);
                
                // If room was deleted (404) or forbidden (403), do not retry
                if (err.status === 404 || err.status === 403) {
                    console.warn('[LiveKit] Room is gone. Stopping retries.');
                    cleanupAllParticipants();
                    dispatch('lk:disconnected', {});
                    window.STTEngine?.stop();
                    return;
                }

                if (reconnectCount < MAX_RECONNECTS) {
                    scheduleReconnect(roomName, participantName, role);
                } else {
                    cleanupAllParticipants();
                    dispatch('lk:disconnected', {});
                    window.STTEngine?.stop();
                }
            }
        }, delay);
    }

    // ── Broadcast STT to all other participants (FINAL ONLY) ─────────────────
    // FIX: interim results are shown locally but NOT sent over the network.
    // This prevents flooding the data channel with ~5-10 packets/second.
    function broadcastTranscription(text, isFinal) {
        if (!room || !isConnected) return;
        if (!isFinal) return; // ← KEY FIX: skip interim over network

        const payload = new TextEncoder().encode(JSON.stringify({
            type:     'transcription',
            identity: localIdentity,
            name:     localName,
            role:     localRole,
            text,
            isFinal: true,
        }));

        room.localParticipant.publishData(payload, { reliable: true });
    }

    // ── Controls ─────────────────────────────────────────────────────────────
    async function toggleMic() {
        if (!room) return false;
        const currentlyEnabled = room.localParticipant.isMicrophoneEnabled;
        const newState = !currentlyEnabled;
        await room.localParticipant.setMicrophoneEnabled(newState);
        window.STTEngine?.setMuted(!newState);
        dispatch('lk:mic-toggled', { enabled: newState });
        return newState;
    }

    async function toggleCamera() {
        if (!room) return false;
        const currentlyEnabled = room.localParticipant.isCameraEnabled;
        const newState = !currentlyEnabled;
        await room.localParticipant.setCameraEnabled(newState);
        dispatch('lk:cam-toggled', { enabled: newState });
        return newState;
    }

    async function toggleScreenShare() {
        if (!room) return false;
        const sharing = room.localParticipant.isScreenShareEnabled;
        const newState = !sharing;
        await room.localParticipant.setScreenShareEnabled(newState);
        return newState;
    }

    function disconnect() {
        clearTimeout(reconnectTimer);
        reconnectCount = MAX_RECONNECTS; // Prevent auto-reconnect
        window.STTEngine?.stop();
        if (room) {
            room.disconnect();
            room = null;
        }
        isConnected = false;
        cleanupAllParticipants();
    }

    function getRoom()         { return room; }
    function getState()        { return { isConnected, localIdentity, localName, localRole }; }
    function getParticipants() { return participants; }

    // ── Wire local STT → LiveKit broadcast ───────────────────────────────────
    // Only broadcast FINAL results to avoid flooding the data channel.
    // Interim results are shown locally via 'stt:interim' event in integra-session.js.
    window.addEventListener('stt:final', (e) => {
        broadcastTranscription(e.detail.text, true);
    });

    // stt:interim is intentionally NOT wired to broadcastTranscription anymore.

    // ── Expose ────────────────────────────────────────────────────────────────
    return {
        connect,
        disconnect,
        toggleMic,
        toggleCamera,
        toggleScreenShare,
        broadcastTranscription,
        getRoom,
        getState,
        getParticipants,
    };

})();

window.LiveKitSession = LiveKitSession;

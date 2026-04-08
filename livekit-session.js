/**
 * livekit-session.js — LiveKit Client Integration
 *
 * Responsibilities:
 *  1. Fetch a signed JWT token from Python backend (/api/livekit/token)
 *  2. Connect to LiveKit room using livekit-client SDK
 *  3. Publish local camera + mic
 *  4. Subscribe to remote participants tracks
 *  5. Broadcast STT transcriptions via LiveKit Data Channel
 *  6. Fire DOM custom events for the UI layer to consume
 *
 * ⚠️  The LiveKit URL (wss://...) comes from the backend token response.
 *     API key and secret NEVER touch this file.
 *
 * DOM Events fired on window:
 *   'lk:connected'          → { room, roomName, participantName, role }
 *   'lk:disconnected'       → {}
 *   'lk:participant-joined' → { identity, name, role }
 *   'lk:participant-left'   → { identity, name }
 *   'lk:track-subscribed'   → { identity, kind, track, element? }
 *   'lk:track-unsubscribed' → { identity, kind }
 *   'lk:speaking-changed'   → { speakers: [identity, ...] }
 *   'lk:transcription'      → { identity, name, text, isFinal }
 *   'lk:error'              → { message }
 */

const LiveKitSession = (() => {

    // ── Config ──────────────────────────────────────────────────────────────
    // Only the public backend URL is here — no secrets.
    const BACKEND_URL = window.APP_CONFIG?.backendUrl || 'http://127.0.0.1:8000';

    // ── State ───────────────────────────────────────────────────────────────
    let room           = null;
    let localIdentity  = null;
    let localName      = null;
    let localRole      = null;
    let isConnected    = false;

    // ── Internal helpers ─────────────────────────────────────────────────────
    function dispatch(name, detail = {}) {
        window.dispatchEvent(new CustomEvent(name, { detail }));
    }

    function getRoleFromMetadata(metadata) {
        try {
            return JSON.parse(metadata || '{}').role || 'unknown';
        } catch {
            return 'unknown';
        }
    }

    // Attach a remote audio/video track to a <video> or <audio> element
    function attachTrack(track, participantIdentity) {
        const el = track.kind === 'video'
            ? document.createElement('video')
            : document.createElement('audio');

        el.id        = `track-${participantIdentity}-${track.kind}`;
        el.autoplay  = true;
        el.playsInline = true;
        if (track.kind === 'video') el.muted = false;

        track.attach(el);
        return el;
    }

    // ── Step 1: Get token from Python backend ────────────────────────────────
    async function fetchToken(roomName, participantName, role) {
        const res = await fetch(`${BACKEND_URL}/api/livekit/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ roomName, participantName, role }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        return await res.json(); // { token, url, roomName, participantName, role }
    }

    // ── Step 2: Connect to LiveKit ───────────────────────────────────────────
    async function connect({ roomName, participantName, role }) {
        if (!window.LivekitClient) {
            dispatch('lk:error', { message: 'LiveKit client SDK not loaded. Add the <script> tag.' });
            return;
        }

        const { Room, RoomEvent, Track, ConnectionState } = window.LivekitClient;

        try {
            // 1. Get token from backend
            const tokenData = await fetchToken(roomName, participantName, role);
            localIdentity  = participantName;
            localName      = participantName;
            localRole      = role;

            // 2. Create room
            room = new Room({
                adaptiveStream: true,
                dynacast: true,
                videoCaptureDefaults: {
                    resolution: { width: 1280, height: 720, frameRate: 30 }
                },
            });

            // 3. Wire events
            room.on(RoomEvent.ConnectionStateChanged, (state) => {
                if (state === ConnectionState.Connected) {
                    isConnected = true;
                    dispatch('lk:connected', {
                        room,
                        roomName,
                        participantName,
                        role,
                    });

                    // Start STT after connection
                    if (window.STTEngine?.isSupported()) {
                        window.STTEngine.start({
                            identity: participantName,
                            name: participantName,
                            lang: 'ar-SA',
                        });
                    }
                }

                if (state === ConnectionState.Disconnected) {
                    isConnected = false;
                    dispatch('lk:disconnected', {});
                    window.STTEngine?.stop();
                }
            });

            room.on(RoomEvent.ParticipantConnected, (participant) => {
                const role = getRoleFromMetadata(participant.metadata);
                dispatch('lk:participant-joined', {
                    identity: participant.identity,
                    name: participant.name || participant.identity,
                    role,
                });
            });

            room.on(RoomEvent.ParticipantDisconnected, (participant) => {
                dispatch('lk:participant-left', {
                    identity: participant.identity,
                    name: participant.name || participant.identity,
                });
            });

            room.on(RoomEvent.TrackSubscribed, (track, _pub, participant) => {
                const el = attachTrack(track, participant.identity);
                dispatch('lk:track-subscribed', {
                    identity: participant.identity,
                    kind: track.kind,
                    track,
                    element: el,
                });
            });

            room.on(RoomEvent.TrackUnsubscribed, (track, _pub, participant) => {
                dispatch('lk:track-unsubscribed', {
                    identity: participant.identity,
                    kind: track.kind,
                });
            });

            room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
                dispatch('lk:speaking-changed', {
                    speakers: speakers.map(s => s.identity),
                });
            });

            // Receive STT transcriptions broadcasted by other participants
            room.on(RoomEvent.DataReceived, (payload, participant) => {
                try {
                    const data = JSON.parse(new TextDecoder().decode(payload));
                    if (data.type === 'transcription') {
                        dispatch('lk:transcription', {
                            identity: participant?.identity || data.identity,
                            name:     data.name,
                            text:     data.text,
                            isFinal:  data.isFinal,
                        });
                    }
                } catch (_) {}
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

    // ── Publish an STT result to all other participants ───────────────────────
    function broadcastTranscription(text, isFinal) {
        if (!room || !isConnected) return;

        const payload = new TextEncoder().encode(JSON.stringify({
            type: 'transcription',
            identity: localIdentity,
            name: localName,
            text,
            isFinal,
        }));

        room.localParticipant.publishData(payload, { reliable: true });
    }

    // ── Controls ──────────────────────────────────────────────────────────────
    async function toggleMic() {
        if (!room) return;
        const enabled = room.localParticipant.isMicrophoneEnabled;
        await room.localParticipant.setMicrophoneEnabled(!enabled);
        window.STTEngine?.setMuted(enabled); // mute STT when mic is muted
        return !enabled;
    }

    async function toggleCamera() {
        if (!room) return;
        const enabled = room.localParticipant.isCameraEnabled;
        await room.localParticipant.setCameraEnabled(!enabled);
        return !enabled;
    }

    async function toggleScreenShare() {
        if (!room) return;
        const sharing = room.localParticipant.isScreenShareEnabled;
        await room.localParticipant.setScreenShareEnabled(!sharing);
        return !sharing;
    }

    function disconnect() {
        window.STTEngine?.stop();
        if (room) {
            room.disconnect();
            room = null;
        }
        isConnected = false;
    }

    function getRoom() { return room; }
    function getState() { return { isConnected, localIdentity, localName, localRole }; }

    // ── Wire STT → LiveKit broadcast ──────────────────────────────────────────
    // Listen for final STT results and broadcast them through the data channel
    window.addEventListener('stt:final', (e) => {
        broadcastTranscription(e.detail.text, true);
    });

    window.addEventListener('stt:interim', (e) => {
        broadcastTranscription(e.detail.text, false);
    });

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
    };

})();

window.LiveKitSession = LiveKitSession;

# TODO - WhatsApp-like Voice Notes (Record + Send Audio Message)

## Goal
Add a WhatsApp-like “hold-to-record” (or tap-to-record) voice note UI that records audio in the browser and sends it as an `audio` message.

## Current state
- Backend already supports audio messages via `media_file` upload (`ALLOWED_MEDIA_EXTENSIONS` includes mp3/wav/ogg/m4a).
- Chat UI supports sending an audio **file** upload, and renders received audio as `<audio controls>`.
- Missing: in-browser recording (mic button + MediaRecorder) to create the audio blob and send it.

## Implementation Plan
1. **templates/messages.html**
   - Add UI controls: mic button + optional timer + stop/send button.
   - Add JS using `MediaRecorder`:
     - Request microphone permission
     - Start recording on click/hold
     - Stop recording
     - Convert blob to `File`
     - Put it into `media-file` (or send via `FormData`) and submit as `/send_message`.
   - Ensure audio messages are classified as `media_type='audio'` by backend.

2. **static/css/style.css**
   - Add styles for mic button/recording state (red dot, “Recording…” label).

3. **(Optional) backend/app.py**
   - No change needed if we send using existing `/send_message` with `media_file`.
   - If browser sends a codec/extension not in allowed list, add fallback mapping.

## Acceptance Criteria
- User can record a voice note and it appears in the chat as an outgoing audio bubble (right side).
- Receiver sees it immediately (Socket.IO new_message) and can play it.
- Works without breaking existing text/media upload.


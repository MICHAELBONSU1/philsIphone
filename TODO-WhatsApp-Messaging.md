# WhatsApp-like Messaging Upgrade Checklist

## Plan (confirmed)
- Implement: (1) real-time messaging, (2) read receipts/unread counts, (3) typing indicator, (4) all of the above.

## Steps
1. [ ] backend/app.py: Add Socket.IO server-side events for chat delivery + typing + join user room
2. [ ] backend/app.py: Mark messages as read when thread is opened (server route or Socket.IO event)
3. [ ] backend/app.py: Update `/api/unread_messages_count` to use `Message.is_read`
4. [ ] backend/app.py: Emit `new_message` to receiver room on `/send_message`
5. [ ] templates/messages.html: Add Socket.IO client listeners; update UI on incoming messages
6. [ ] templates/messages.html: On selecting a conversation, call mark-read + update badges
7. [ ] templates/messages.html: Add typing indicator UI and send typing events
8. [ ] static/css/style.css: Styling for typing indicator / read receipts
9. [ ] Smoke test with 2 browser sessions: send, receive instantly, unread counts decrease, typing indicator works
10. [ ] Finalize


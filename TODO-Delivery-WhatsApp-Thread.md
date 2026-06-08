# TODO - Delivery Messaging Thread (3-party + unlock)

- [x] Step 1: Add `DeliveryMessage` SQLAlchemy model (delivery-scoped) to `backend/app.py` (or a better location if refactor exists).

- [x] Step 2: Add DB migration/make tables with `db.create_all()` (and ensure columns exist).
- [x] Step 3: Add backend API routes:
  - [x] POST `/api/delivery_messages/send`
  - [x] GET `/api/delivery_messages/<int:delivery_id>?other_id=...`
  - [x] (optional) Socket.IO events for realtime + read receipt if needed.
- [x] Step 4: Add Socket.IO server events for delivery chat:
  - [x] join rooms: ensure sender/recipient/rider rooms are used
  - [x] emit `delivery_new_message` to appropriate participants
- [x] Step 5: Delivery page UI updates:
  - [x] `templates/delivery_sender.html` add a Messages panel with chat + send
  - [x] `templates/delivery_recipient.html` add same Messages panel
  - [x] `templates/delivery_admin.html` add same Messages panel
- [x] Step 6: Frontend JS for delivery chat:
  - [x] unlock gating based on Delivery.status
  - [x] load messages and mark read
  - [x] send text/media
- [ ] Step 7: Testing (3 accounts):
  - [ ] Locked before sender req + recipient approve + rider accept
  - [ ] Unlocked after rider accept
  - [ ] Sender can message recipient + rider; recipient can message sender + rider; rider can message sender + recipient
- [ ] Step 8: Smoke test + fix any missing endpoints/assets.

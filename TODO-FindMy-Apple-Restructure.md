# TODO: Apple-style Find My Phone restructure

## Plan execution steps
- [x] Step 1: Add DB models `TrackedDevice` and `DeviceShare` in `backend/app.py` (pending implementation)
- [ ] Step 2: Add migration logic / `db.create_all()` compatibility updates.
- [ ] Step 3: Implement new token-scoped APIs:
  - [ ] `POST /api/device/update_location`
  - [ ] `GET /api/device/current_location`
  - [ ] `POST /api/device/trigger_alarm`
  - [ ] `POST /api/device/remote_lock`
  - [ ] `POST /api/device/remote_unlock`
- [ ] Step 4: Add Socket.IO rooms & events for real-time device updates:
  - [ ] join device rooms
  - [ ] emit `device_location_update` to viewers
- [ ] Step 5: Split UI screens:
  - [ ] `templates/find_my_phone_owner.html`
  - [ ] `templates/find_my_phone_device_agent.html`
  - [ ] update `templates/find_my_phone.html` into viewer share-link/code UI
- [ ] Step 6: Replace hardcoded `UNLOCK_PIN = "1234"` with per-device PIN (hashed) + verification.
- [ ] Step 7: Remove/disable legacy user-based endpoints or keep as backward compatible.
- [ ] Step 8: Manual test flow end-to-end.


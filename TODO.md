## Delivery UI role separation (sender vs recipient)

### Info gathered
- `backend/app.py` contains a single `/delivery` page route rendering `templates/delivery.html`.
- Socket.IO rooms already exist:
  - `user:{sender_id}`
  - `user:{recipient_id}`
  - `rider:{driver_id}`
- Live update emitters:
  - `/api/request_delivery` emits `delivery_offer` to `room=rider:{matched.id}`.
  - `/api/rider_accept_delivery` emits `delivery_status_update` to `user:{sender_id}`, `user:{recipient_id}`, and `rider:{driver_id}`.
  - `/api/confirm_handover` and `/api/process_payment` emit `delivery_status_update` to the same rooms.
- Current UI issue: `templates/delivery.html` mixes sender inputs (recipient_id + pickup/dropoff + request) with rider/driver controls (start live updates) and recipient tracking, so roles are visually indistinguishable.

### Plan (high level)
1. Create role-specific templates:
   - `templates/delivery_sender.html`
   - `templates/delivery_recipient.html`
   - `templates/delivery_driver.html` (optional; `delivery_admin.html` may already serve driver role)
2. Add new Flask routes:
   - `/delivery/sender`
   - `/delivery/recipient`
   - (keep `/delivery` for backward compatibility or redirect)
3. Update templates to:
   - join correct Socket.IO rooms:
     - sender: join `user:{session.user_id}` and optionally `delivery:{delivery_id}`
     - recipient: join `user:{session.user_id}`
   - render role-specific controls only:
     - Sender: request delivery + status timeline
     - Recipient: track map + handover/paid indicators
     - Driver: accept + handover + paid (use existing `delivery_admin.html` logic or new template)
4. Add small common JS helper or duplicate minimal logic for each template.
5. Ensure `rider_location_update` is handled on recipient UI (needs `socket.emit('join_delivery', ...)` or `join_delivery` plus `delivery:{delivery_id}` room).
6. Test manually with 3 browser tabs (sender/recipient/driver) and verify that:
   - sender sees only sender-specific controls and timeline updates
   - recipient sees tracking/map and handover/paid updates
   - driver sees only driver controls

### Dependent files to edit
- `backend/app.py`
- `templates/delivery.html` (may be deprecated/redirect)
- `templates/delivery_admin.html` (driver portal, if needed)
- `templates/base.html` (nav delivery links if we want role-based entry points)

### Followup steps
- Run the server and open 3 sessions/tabs.
- Confirm Socket.IO events are rendered only in the correct role pages.


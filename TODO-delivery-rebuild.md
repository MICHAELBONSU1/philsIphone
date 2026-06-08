# TODO - Delivery rebuild

## Goal
Rebuild the delivery UI “solid” across all current delivery templates.

## Checklist
- [ ] Update `templates/delivery_sender.html` (solid booking UI, live tracking, ETA widget, notifications center)
- [ ] Update `templates/delivery_recipient.html` (approval + live tracking + notifications center)
- [ ] Update `templates/delivery_admin.html` (driver portal + live tracking + notifications center)
- [ ] Update `templates/delivery_recipient_senderid.html` (sender-id lookup + live tracking + notifications center)
- [ ] Update legacy `templates/delivery.html` to redirect/bridge to the new UI (or make it solid)
- [ ] Add solid ETA widget based on GPS updates (no external APIs)
- [ ] Add Notifications Center UI panel wired to `system_notification` + delivery updates
- [ ] Smoke test with 3 tabs:
  - [ ] Sender creates delivery
  - [ ] Recipient receives approval + can approve
  - [ ] Rider/driver accepts + sees route + can advance statuses

## Notes
No backend changes planned unless templates reveal missing payload fields.

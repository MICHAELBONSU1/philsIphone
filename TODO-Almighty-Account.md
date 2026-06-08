# TODO - Almighty Account (System Admin)

## Goal
Create a second special account ("almighty") that can manage the entire system: users, posted items, approvals (approve/revoke), and view/control on an admin interface.

## Current State
- Existing admin account: `phil` (created automatically in `backend/app.py` with `is_admin=True`, `can_post=True`).
- Admin UI exists at `/admin_panel` (template: `templates/admin_panel.html`) and supports:
  - Approve posting requests
  - Approve/revoke user posting permissions
  - View pending/approved sellers

## Planned Implementation
1. Add new “almighty” account creation in `backend/app.py` (migrations safe) if not exists.
2. Add/extend admin UI to allow:
   - Manage all users: approve/revoke can_post
   - View/delete items (global), not only items per seller
   - (Optional) view requests for approve/reject
3. Add new routes for almighty:
   - `/<almighty_admin_route>` or reuse `/admin_panel` with a stronger permission flag
   - Item management routes for almighty (list items + delete)
4. Update templates:
   - New `templates/almighty_panel.html` or extend `templates/admin_panel.html`
5. Permission logic:
   - Introduce `is_almighty` flag (preferred) OR treat as `is_admin` plus whitelist username.
6. Test:
   - Login as almighty and verify every management action.
   - Login as normal admin (phil) to ensure backward compatibility.


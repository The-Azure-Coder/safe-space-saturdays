# Safe Space Saturdays admin portal

The admin portal is available at `/admin` and is protected by the API, not just by hidden navigation. A user must have `role = 'admin'` to read or change reports, users, or quotes.

## Promote an administrator

Run this once against the intended production database, replacing the email with the trusted account:

```sql
UPDATE users SET role = 'admin' WHERE email = 'trusted-admin@example.com';
```

For the local Docker database, the equivalent command is:

```bash
docker compose exec db psql -U app -d app -c "UPDATE users SET role = 'admin' WHERE email = 'trusted-admin@example.com';"
```

After promotion, sign out and back in so the profile menu receives the updated role. Password resets invalidate all active sessions for the affected user. The reset password is never logged or returned by the API.

## User bug reports

Signed-in members can open the floating `Report a bug` launcher. Reports capture the title, description, severity, page path, browser user-agent, and reporter identity. Members are instructed not to include private journal content.

## Admin API surface

- `GET/PATCH /api/admin/bug-reports`
- `GET/PATCH /api/admin/users`
- `POST /api/admin/users/{id}/password-reset`
- `GET/POST/PATCH/DELETE /api/admin/quotes`

All admin endpoints require the authenticated session and an administrator role. List endpoints are paginated and mutation payloads are validated with Pydantic schemas.

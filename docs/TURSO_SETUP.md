# Durable Storage Setup — Turso (libSQL)

The Saka backend stores all patient data in **Turso**, a free, durable,
SQLite-compatible cloud database. This is what stops patients from disappearing
when Render's free-tier container restarts (its local filesystem is ephemeral).

The backend chooses its storage automatically:

| Environment | `TURSO_DATABASE_URL` | Backend used |
|-------------|----------------------|--------------|
| Production (Render) | set | Turso (durable, survives restarts) |
| Local dev / tests | unset | local SQLite file (`doctors.db`) |

No SQL changed — libSQL speaks the SQLite dialect, so only the connection layer
in `backend/services/database.py` is backend-aware.

## One-time setup (~5 minutes, free)

1. **Install the Turso CLI** and sign up (free, no card):
   ```bash
   curl -sSfL https://get.tur.so/install.sh | bash
   turso auth signup
   ```

2. **Create the database** (pick a region near your users, e.g. `fra`/`jnb`):
   ```bash
   turso db create saka --location fra
   ```

3. **Grab the two values Render needs:**
   ```bash
   turso db show saka --url        # -> TURSO_DATABASE_URL  (libsql://saka-<org>.turso.io)
   turso db tokens create saka     # -> TURSO_AUTH_TOKEN     (long JWT string)
   ```

4. **Set them on the Render backend service** → *Environment* tab:
   - `TURSO_DATABASE_URL` = the `libsql://…` URL
   - `TURSO_AUTH_TOKEN`   = the token
   Save; Render redeploys. Tables are created automatically on first boot.

That's it. Patients created after this persist across restarts, sleeps and
redeploys.

## Verifying it works

- **Health check:** `GET /health` should be `healthy` after deploy.
- **Inspect data directly** from your laptop:
  ```bash
  turso db shell saka "SELECT COUNT(*) FROM patients;"
  ```
- **Local dev** needs nothing — leave the vars unset and it uses a local
  `doctors.db` file exactly as before.

## Notes

- **Free tier limits** (plenty for the pilot): 500 databases, 9 GB storage,
  1 billion row-reads/month.
- **Backups:** `turso db shell saka .dump > backup.sql` for a point-in-time copy.
- **Migrating existing local data** into Turso, if you have a `doctors.db` you
  want to keep:
  ```bash
  sqlite3 doctors.db .dump | turso db shell saka
  ```

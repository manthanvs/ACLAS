# After deployment: connect, sign in, update, back up

Companion to [DEPLOY.md](DEPLOY.md). Replace `YOURNAME` with your PythonAnywhere username everywhere.
Menu names on third-party sites (Google, PythonAnywhere) change over time; if a label differs, look for the closest match.

---

## 6. Point the VS Code extension at your server

The extension sends a heartbeat (a small JSON POST) every 30 seconds to the URL in the `aclas.serverEntrypoint` setting. The default is `http://localhost:8000/api/heartbeats/`, which only works on your own machine.

### 6.1 Get your API token
1. Open `https://YOURNAME.pythonanywhere.com/` and sign in.
2. Go to **Settings** (top bar). Copy the value under **API Token**, or use **Copy Token** on the Dashboard.
3. Treat it like a password. Anyone with it can write data as you. If it leaks, an admin can delete it in `/admin/` → **Auth Token → Tokens**; a new one is generated the next time you open the dashboard.

### 6.2 Set the server URL
Either through the UI:
1. In VS Code open **File → Preferences → Settings** (`Ctrl+,`).
2. Search `aclas`.
3. Set **Aclas: Server Entrypoint** to
   `https://YOURNAME.pythonanywhere.com/api/heartbeats/`
   (keep the trailing slash; Django redirects POSTs without it and the redirect can drop the request body).

Or in `settings.json` (`Ctrl+Shift+P` → *Preferences: Open User Settings (JSON)*):
```json
{
  "aclas.serverEntrypoint": "https://YOURNAME.pythonanywhere.com/api/heartbeats/"
}
```
Use **User** settings to apply it everywhere, or **Workspace** settings for one project.

### 6.3 Enter the token
1. `Ctrl+Shift+P` → **ACLAS: Enter API Token**.
2. Paste the token. It is stored in VS Code's secret storage (not in settings files).
3. On a fresh install, the extension also offers an **Enter Token** button on first run.

### 6.4 Verify it works
1. Open any file in a folder and type for about a minute. A heartbeat is sent only after real edits (added or deleted lines).
2. Refresh `https://YOURNAME.pythonanywhere.com/dashboard/`. **Total Events** should be 1 or more.
3. Quick manual test from any terminal (replace the token):
```bash
curl -i -X POST https://YOURNAME.pythonanywhere.com/api/heartbeats/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_name":"test","language":"python","lines_added":1}'
```
Expected: `HTTP 201` and `{"status":"Heartbeat recorded"}`.

### 6.5 Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| Nothing on the dashboard | No token entered, or you have not typed since the last tick | Run *ACLAS: Enter API Token*; edit a file; wait 30–60 s |
| Dev Tools console shows `heartbeat rejected (401)` | Wrong or deleted token | Re-copy the token from Settings |
| `rejected (400)` | Payload fails validation | Update the extension and server to the same version |
| `rejected (403)` or CSRF error in browser forms | `DJANGO_CSRF_ORIGINS` missing or wrong | Must be `https://YOURNAME.pythonanywhere.com` (with `https://`, no trailing slash); Reload |
| `Failed to send heartbeat` / timeout | URL typo, site down, or app disabled (free tier) | Open the URL in a browser; click **Reload** or **Run until...** in the Web tab |
| 400 "Bad Request (400)" page | `DJANGO_ALLOWED_HOSTS` does not match | Must be exactly `YOURNAME.pythonanywhere.com`; Reload |
| Redirect loop on HTTPS | Proxy header not trusted | Already handled by `SECURE_PROXY_SSL_HEADER`; confirm `DJANGO_DEBUG=0` is read from `.env` |

To see extension logs: **Help → Toggle Developer Tools → Console**, filter by `ACLAS`.
To see server logs: PythonAnywhere **Web** tab → **Log files** → *error log* and *server log*.

---

## 7. Google sign-in (optional)

Email and password login works without any of this. Do this only if you want the **Continue with Google** button to work.

### 7.1 Create the OAuth client (free)
1. Go to <https://console.cloud.google.com/> and sign in.
2. Create a project (top bar → project picker → **New project**), e.g. `ACLAS`.
3. **APIs & Services → OAuth consent screen** (may appear as *Google Auth Platform*):
   - User type: **External**.
   - App name `ACLAS`, your email as support and developer contact.
   - Scopes: the defaults (`email`, `profile`, `openid`) are enough.
   - While the app is in **Testing**, add each Google account that should be able to sign in under **Test users** (limit 100). Publishing to *Production* avoids that list but, for these basic scopes, normally needs no Google review.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Application type: **Web application**.
   - **Authorized JavaScript origins:** `https://YOURNAME.pythonanywhere.com`
   - **Authorized redirect URIs:**
     `https://YOURNAME.pythonanywhere.com/accounts/google/login/callback/`
     (exact match, including the trailing slash)
5. Copy the **Client ID** and **Client secret**. The secret is shown in the credential details; keep it private and never commit it.

For local testing add a second redirect URI:
`http://127.0.0.1:8000/accounts/google/login/callback/`

### 7.2 Register it in Django admin
1. Open `https://YOURNAME.pythonanywhere.com/admin/` and sign in with the superuser from DEPLOY.md step 4.
2. **Sites → Sites**: confirm the site with ID **1** has domain `YOURNAME.pythonanywhere.com`. (Production uses `DJANGO_SITE_ID=1`.)
3. **Social accounts → Social applications → Add**:
   - Provider: **Google**
   - Name: `ACLAS Google`
   - Client id / Secret key: from step 7.1
   - **Sites:** move `YOURNAME.pythonanywhere.com` into *Chosen sites*.
4. Save. Delete any leftover placeholder Google app (the dev helper `fix_site.py` creates one with dummy credentials; a fresh server does not have it).

### 7.3 Test
Sign out, open the login page, click **Continue with Google**, and complete the consent screen. You land on the dashboard. A new local user is created from your Google email.

### 7.4 Common Google errors
| Error | Cause / fix |
|---|---|
| `redirect_uri_mismatch` | URI in Google Console is not byte-identical to the one above (http vs https, missing trailing slash, wrong username) |
| `access_denied` / "app not verified" | You are not on the **Test users** list while in Testing mode |
| `SocialApp.DoesNotExist` page | No Google app in admin, or it is not attached to Site 1 |
| Works locally, not live | `DJANGO_SITE_ID` does not match the site that has the app attached |

PythonAnywhere free accounts can only reach an allow-list of external hosts from the server; Google's OAuth endpoints are on that list at the time of writing, but check their current allow-list page if the callback times out.

---

## Updating the deployment

Run in a PythonAnywhere **Bash console**:
```bash
cd ~/ACLAS
cp aclas_backend/db.sqlite3 ~/db-backup-$(date +%F).sqlite3   # always back up first
git pull
source ~/venv/bin/activate
cd aclas_backend
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```
Then **Web** tab → green **Reload** button. Skipping Reload means the old code keeps running.

Checklist after each update:
1. Dashboard loads and shows your old data.
2. Send a test heartbeat (6.4).
3. Check the error log for new tracebacks.

Rolling back:
```bash
git log --oneline          # find the last good commit
git checkout <commit>      # or: git revert <bad-commit>
cp ~/db-backup-YYYY-MM-DD.sqlite3 aclas_backend/db.sqlite3   # only if a migration broke data
```
Reload again afterwards. Migrations are not automatically reversible; restoring the backup is the safe path.

If you change `.env`, Reload is also required.

---

## Keeping the free app alive

Free PythonAnywhere web apps are disabled after a period unless you extend them. Every month (your Web tab shows the exact date), open the **Web** tab and click **Run until 1 month from today**. Put a calendar reminder in; PythonAnywhere also emails a warning beforehand. Check their current policy, as the interval can change.

---

## Caveat: SQLite on free hosting

SQLite is a single file. It is fine for a personal or university deployment with a handful of users, but not for many concurrent users, because writers lock the whole database and each developer sends a write every 30 seconds.

Practical limits and mitigations:
- **Roughly 10–20 active developers** is a sensible ceiling before you see `database is locked` errors; the heartbeat failure is silent on the extension side, so data is dropped rather than queued.
- **Back up regularly.** The database holds all telemetry:
  - Manual: download `~/ACLAS/aclas_backend/db.sqlite3` from the PythonAnywhere **Files** tab.
  - Scheduled (Tasks tab, free daily task):
    `cp ~/ACLAS/aclas_backend/db.sqlite3 ~/backups/db-$(date +\%F).sqlite3`
    (create `~/backups` first; the `\%` escape is required in cron-style fields). Delete old copies occasionally, as free storage is limited (about 500 MB).
- **Never commit `db.sqlite3` or `.env`.** Both are in `.gitignore`.
- **Outgrowing it:** switch `DATABASES` to PostgreSQL (e.g. a managed free tier or a paid host), run `python manage.py dumpdata` / `loaddata` to move data, and keep the same settings otherwise.
- **Privacy:** the database contains filenames, project names and activity patterns of every user. Tell users what you store, restrict `/admin/` to yourself, and delete a user's rows if they ask.

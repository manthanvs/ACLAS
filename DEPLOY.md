# Deploying the ACLAS dashboard (free)

Free option: **PythonAnywhere (Beginner account)** — no card, SQLite works, HTTPS included at `yourname.pythonanywhere.com`.
Free-tier limits: one web app, sleeps/expires unless you click "Run until 3 months from today" periodically, outbound internet restricted (fine here; Google sign-in works only to allow-listed Google domains).

## 1. Account
Sign up at pythonanywhere.com (Beginner). Note your username.

## 2. Get the code (Bash console)
```bash
git clone https://github.com/manthanvs/ACLAS.git
cd ACLAS/aclas_backend
python3.13 -m venv ~/venv && source ~/venv/bin/activate   # use any Python >= 3.12 offered
pip install -r requirements.txt
```

## 3. Configure
```bash
cp .env.example .env && nano .env
```
Set:
```
DJANGO_SECRET_KEY=<python -c "import secrets;print(secrets.token_urlsafe(60))">
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=YOURNAME.pythonanywhere.com
DJANGO_CSRF_ORIGINS=https://YOURNAME.pythonanywhere.com
DJANGO_SITE_ID=1
```

## 4. Database + static
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py shell -c "from django.contrib.sites.models import Site; Site.objects.filter(id=1).update(domain='YOURNAME.pythonanywhere.com', name='ACLAS')"
```

## 5. Web tab → Add a new web app → Manual configuration (same Python version)
- Virtualenv: `/home/YOURNAME/venv`
- Source code: `/home/YOURNAME/ACLAS/aclas_backend`
- Edit the WSGI file: replace its contents with
```python
import sys
sys.path.insert(0, '/home/YOURNAME/ACLAS/aclas_backend')
from aclas.wsgi import application
```
- Static files: URL `/static/` → `/home/YOURNAME/ACLAS/aclas_backend/staticfiles` (WhiteNoise also serves them, so this is optional).
- Click **Reload**.

## 6. Point the extension at it
VS Code Settings → `aclas.serverEntrypoint` = `https://YOURNAME.pythonanywhere.com/api/heartbeats/`

## 7. Google sign-in (optional)
Create an OAuth client in Google Cloud Console (free), redirect URI
`https://YOURNAME.pythonanywhere.com/accounts/google/login/callback/`, then add the client ID/secret as a Social Application in `/admin/` and attach Site 1. Email/password works without this.

## Updating
`git pull && source ~/venv/bin/activate && python manage.py migrate && python manage.py collectstatic --noinput`, then Reload on the Web tab.

## Caveat
SQLite on free hosting is fine for a personal/university deployment, not for many concurrent users. Back up `db.sqlite3` before upgrades.

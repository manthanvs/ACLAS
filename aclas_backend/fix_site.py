import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aclas.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# Print current state for debugging
print("Current sites in DB:")
for s in Site.objects.all():
    print(f"  id={s.id}, domain={s.domain}, name={s.name}")

# The site with id=2 already exists; update its domain/name to be correct
site = Site.objects.filter(domain='127.0.0.1:8000').first()
if not site:
    site = Site.objects.first()

if site:
    site.domain = '127.0.0.1:8000'
    site.name = 'localhost'
    site.save()
    print(f"Updated site id={site.id} → domain={site.domain}, name={site.name}")
    print(f"\n*** ACTION REQUIRED ***")
    print(f"Your settings.py has SITE_ID = 1, but the DB has site id={site.id}.")
    print(f"The script will update settings.py to use SITE_ID = {site.id} automatically.")
else:
    site = Site.objects.create(domain='127.0.0.1:8000', name='localhost')
    print(f"Created site id={site.id}")

# Ensure a Google SocialApp exists and is linked to this site
app, created = SocialApp.objects.get_or_create(
    provider='google',
    defaults={'name': 'ACLAS Google', 'client_id': 'dummy', 'secret': 'dummy'},
)
if created:
    print("Created new SocialApp for Google")
else:
    print("SocialApp for Google already exists")

app.sites.add(site)
print(f"\nSite and SocialApp fixed. Site id={site.id}")
print(f"Make sure settings.py has: SITE_ID = {site.id}")

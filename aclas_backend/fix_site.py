import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aclas.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

site, _ = Site.objects.get_or_create(id=1, defaults={'domain': '127.0.0.1:8000', 'name': 'localhost'})
app, _ = SocialApp.objects.get_or_create(provider='google', defaults={'name':'ACLAS Google', 'client_id': 'dummy', 'secret': 'dummy'})
app.sites.add(site)
print('Site and SocialApp fixed successfully.')

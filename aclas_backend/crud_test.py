import os
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aclas.settings')
django.setup()

from django.contrib.auth.models import User
from telemetry.models import TelemetryEvent
from django.utils import timezone

print('=== Starting CRUD Operations ===')

# 1. CREATE
user, created = User.objects.get_or_create(username='test_dev', email='dev@aclas.com')
if created:
    user.set_password('password123')
    user.save()
    print('Created user test_dev')

event = TelemetryEvent.objects.create(
    user=user,
    language='Python',
    project_name='ACLAS_Project',
    lines_added=50,
    lines_deleted=10
)
print(f'CREATED: {event}')

# 2. READ
events = TelemetryEvent.objects.filter(project_name='ACLAS_Project')
print(f'READ: Found {events.count()} events for ACLAS_Project')

# 3. UPDATE
event_to_update = events.first()
event_to_update.language = 'Django/Python'
event_to_update.save()
print(f'UPDATED: Language is now {event_to_update.language}')

# 4. DELETE
# We will delete the event to clean up, or keep it to verify in admin.
# Wait, we better keep it so we can verify the admin panel in Assignment 2.
# Let me create a temporary one to delete.
temp_event = TelemetryEvent.objects.create(
    user=user,
    language='JavaScript',
    project_name='Temp_Project'
)
print(f'Created temp event to delete: {temp_event}')
temp_event.delete()
print('DELETED: temp_event successfully deleted.')

print('=== Finished CRUD Operations ===')

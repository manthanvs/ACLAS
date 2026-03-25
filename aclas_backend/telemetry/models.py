from django.db import models
from django.contrib.auth.models import User

class TelemetryEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telemetry_events')
    language = models.CharField(max_length=100)
    project_name = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    lines_added = models.IntegerField(default=0)
    lines_deleted = models.IntegerField(default=0)
    active_seconds = models.IntegerField(default=0)  # time actively coding
    idle_seconds = models.IntegerField(default=0)    # time idle (no keystrokes)

    def __str__(self):
        return f"{self.user.username} - {self.language} at {self.timestamp}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=50)
    preferred_language = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


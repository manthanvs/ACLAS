from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class TelemetryEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telemetry_events')
    language = models.CharField(max_length=100)
    project_name = models.CharField(max_length=255)
    file = models.CharField(max_length=500, blank=True, default='')   # relative path sent by extension
    timestamp = models.DateTimeField(default=timezone.now)            # client-side timestamp
    received_at = models.DateTimeField(auto_now_add=True)             # server receive time
    lines_added = models.IntegerField(default=0)
    lines_deleted = models.IntegerField(default=0)
    active_seconds = models.IntegerField(default=0)   # time actively coding
    idle_seconds = models.IntegerField(default=0)     # time idle (no keystrokes)

    # ── Stress Metrics ────────────────────────────────────────────────
    errors = models.IntegerField(default=0)           # diagnostic errors (5-s poll)
    repeated_errors = models.IntegerField(default=0)  # same error across polls
    build_runs = models.IntegerField(default=0)       # task executions
    build_failures = models.IntegerField(default=0)   # builds that ended with errors
    file_switches = models.IntegerField(default=0)    # editor tab switches
    undo_count = models.IntegerField(default=0)       # detected undo operations
    terminal_errors = models.IntegerField(default=0)  # failed terminal commands

    @property
    def stress_score(self):
        """Weighted stress score (0–100). Higher = more stress signals."""
        raw = (
            self.errors          * 3 +
            self.repeated_errors * 5 +
            self.build_failures  * 4 +
            self.file_switches   * 1 +
            self.undo_count      * 2 +
            self.terminal_errors * 3
        )
        return min(100, raw)

    def __str__(self):
        return f"{self.user.username} - {self.language} at {self.timestamp}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=50)
    preferred_language = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


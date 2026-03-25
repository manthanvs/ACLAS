from rest_framework import serializers
from .models import TelemetryEvent

class TelemetryEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelemetryEvent
        fields = ['language', 'project_name', 'lines_added', 'lines_deleted', 'active_seconds', 'idle_seconds']

from rest_framework import serializers
from .models import TelemetryEvent

class TelemetryEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelemetryEvent
        fields = [
            'language', 'project_name', 'file', 'timestamp',
            'lines_added', 'lines_deleted',
            'active_seconds', 'idle_seconds',
            # Stress metrics (optional — default to 0 if not sent)
            'errors', 'repeated_errors', 'build_runs', 'build_failures',
            'file_switches', 'undo_count', 'terminal_errors',
        ]
        extra_kwargs = {
            'file':            {'required': False},
            'timestamp':       {'required': False},
            'errors':          {'required': False},
            'repeated_errors': {'required': False},
            'build_runs':      {'required': False},
            'build_failures':  {'required': False},
            'file_switches':   {'required': False},
            'undo_count':      {'required': False},
            'terminal_errors': {'required': False},
        }

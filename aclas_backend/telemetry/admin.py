from django.contrib import admin
from .models import TelemetryEvent

# Customize the admin UI headers and title
admin.site.site_header = "ACLAS Administration"
admin.site.site_title = "ACLAS Admin Portal"
admin.site.index_title = "Welcome to ACLAS Telemetry Portal"

# Register the TelemetryEvent model
@admin.register(TelemetryEvent)
class TelemetryEventAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'project_name', 'file', 'language', 'timestamp', 'received_at',
        'lines_added', 'lines_deleted', 'active_seconds',
        'errors', 'build_runs', 'build_failures', 'file_switches',
        'undo_count', 'terminal_errors',
    )
    list_filter = ('language', 'project_name', 'user')
    search_fields = ('project_name', 'file', 'language', 'user__username')
    readonly_fields = ('received_at',)


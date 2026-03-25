from django.contrib import admin
from .models import TelemetryEvent

# Customize the admin UI headers and title
admin.site.site_header = "ACLAS Administration"
admin.site.site_title = "ACLAS Admin Portal"
admin.site.index_title = "Welcome to ACLAS Telemetry Portal"

# Register the TelemetryEvent model
@admin.register(TelemetryEvent)
class TelemetryEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'project_name', 'language', 'timestamp', 'lines_added', 'lines_deleted')
    list_filter = ('language', 'project_name', 'user')
    search_fields = ('project_name', 'language', 'user__username')

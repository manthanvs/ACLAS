import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from telemetry.models import TelemetryEvent
from rest_framework.authtoken.models import Token

@login_required
def dashboard_view(request):
    api_token, _ = Token.objects.get_or_create(user=request.user)
    events = TelemetryEvent.objects.filter(user=request.user)
    
    total_events = events.count()
    total_additions = events.aggregate(Sum('lines_added'))['lines_added__sum'] or 0
    total_deletions = events.aggregate(Sum('lines_deleted'))['lines_deleted__sum'] or 0
    total_active_secs = events.aggregate(Sum('active_seconds'))['active_seconds__sum'] or 0
    total_idle_secs = events.aggregate(Sum('idle_seconds'))['idle_seconds__sum'] or 0

    def fmt_time(secs):
        h, rem = divmod(int(secs), 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}h {m}m"
        return f"{m}m {s}s"

    # Project Aggregations
    projects = list(events.values('project_name').annotate(
        lines=Sum('lines_added')
    ).order_by('-lines')[:5])

    # Language Aggregations
    languages = list(events.values('language').annotate(
        interactions=Count('id')
    ).order_by('-interactions')[:5])

    context = {
        'api_token': api_token.key,
        'total_events': total_events,
        'total_additions': total_additions,
        'total_deletions': total_deletions,
        'total_active_time': fmt_time(total_active_secs),
        'total_idle_time': fmt_time(total_idle_secs),
        'total_time': fmt_time(total_active_secs + total_idle_secs),
        'projects_json': json.dumps(projects),
        'languages_json': json.dumps(languages)
    }
    return render(request, 'analytics/dashboard.html', context)

@login_required
def stats_view(request):
    events = TelemetryEvent.objects.filter(user=request.user).order_by('-timestamp')[:50]
    return render(request, 'analytics/stats.html', {'events': events})

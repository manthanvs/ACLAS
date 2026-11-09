import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from telemetry.models import TelemetryEvent
from rest_framework.authtoken.models import Token

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'analytics/landing.html')

@login_required
def dashboard_view(request):
    api_token, _ = Token.objects.get_or_create(user=request.user)
    events = TelemetryEvent.objects.filter(user=request.user)

    # One aggregate query for every total (was 3 round-trips)
    s = events.aggregate(
        total_events=Count('id'),
        additions=Sum('lines_added'),
        deletions=Sum('lines_deleted'),
        active=Sum('active_seconds'),
        idle=Sum('idle_seconds'),
        total_errors=Sum('errors'),
        total_repeated=Sum('repeated_errors'),
        total_builds=Sum('build_runs'),
        total_failures=Sum('build_failures'),
        total_switches=Sum('file_switches'),
        total_undos=Sum('undo_count'),
        total_terminal=Sum('terminal_errors'),
    )
    total_events = s['total_events']
    total_additions = s['additions'] or 0
    total_deletions = s['deletions'] or 0
    total_active_secs = s['active'] or 0
    total_idle_secs = s['idle'] or 0
    total_errors    = s['total_errors']    or 0
    total_repeated  = s['total_repeated']  or 0
    total_builds    = s['total_builds']    or 0
    total_failures  = s['total_failures']  or 0
    total_switches  = s['total_switches']  or 0
    total_undos     = s['total_undos']     or 0
    total_terminal  = s['total_terminal']  or 0

    # Weighted stress score (0-100)
    raw_stress = (
        total_errors   * 3 +
        total_repeated * 5 +
        total_failures * 4 +
        total_switches * 1 +
        total_undos    * 2 +
        total_terminal * 3
    )
    avg_stress = min(100, round(raw_stress / total_events, 1) if total_events else 0)

    if avg_stress <= 30:
        stress_level, stress_color = 'Low', 'emerald'
    elif avg_stress <= 60:
        stress_level, stress_color = 'Medium', 'yellow'
    else:
        stress_level, stress_color = 'High', 'red'

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

    # Stress breakdown for radar chart
    stress_breakdown = {
        'Errors':          total_errors,
        'Repeated Errors': total_repeated,
        'Build Failures':  total_failures,
        'File Switches':   total_switches,
        'Undos':           total_undos,
        'Terminal Errors': total_terminal,
    }

    context = {
        'api_token': api_token.key,
        'total_events': total_events,
        'total_additions': total_additions,
        'total_deletions': total_deletions,
        'total_active_time': fmt_time(total_active_secs),
        'total_idle_time': fmt_time(total_idle_secs),
        'total_time': fmt_time(total_active_secs + total_idle_secs),
        'projects_json': json.dumps(projects),
        'languages_json': json.dumps(languages),
        # Stress
        'avg_stress': avg_stress,
        'stress_level': stress_level,
        'stress_color': stress_color,
        'total_builds': total_builds,
        'total_failures': total_failures,
        'stress_breakdown_json': json.dumps(stress_breakdown),
    }
    return render(request, 'analytics/dashboard.html', context)

@login_required
def stats_view(request):
    events = TelemetryEvent.objects.filter(user=request.user).order_by('-timestamp')[:50]
    return render(request, 'analytics/stats.html', {'events': events})

@login_required
def about_view(request):
    return render(request, 'analytics/about.html')

"""
analytics/tests/test_dashboard_views.py
════════════════════════════════════════
Integration tests for analytics views (landing, dashboard, stats, about).

Coverage goals
──────────────
* Landing page: unauthenticated → 200 with HTML
* Landing page: authenticated → redirect to /dashboard/
* Dashboard: unauthenticated → redirect to login
* Dashboard: authenticated → 200, correct context keys
* Dashboard avg_stress formula correctness (Low / Medium / High thresholds)
* Dashboard context: projects_json, languages_json as valid JSON
* Stats view: unauthenticated redirect; authenticated 200 with events
* About view: 200 for authenticated users

Marker: @pytest.mark.integration
Uses: Django TestCase-style assertions via pytest-django
"""
import json
import pytest
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from telemetry.models import TelemetryEvent


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def create_user(username="dev", password="testpass123"):
    return User.objects.create_user(username=username, password=password)


def create_event(user, **kwargs):
    defaults = dict(
        language="Python",
        project_name="ACLAS",
        lines_added=10,
        lines_deleted=2,
        active_seconds=120,
        idle_seconds=30,
    )
    defaults.update(kwargs)
    return TelemetryEvent.objects.create(user=user, **defaults)


# ═════════════════════════════════════════════════════════════════════════════
# Landing View
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.django_db
class TestLandingView:
    def test_unauthenticated_returns_200(self, client):
        response = client.get(reverse("landing"))
        assert response.status_code == 200

    def test_unauthenticated_uses_landing_template(self, client):
        response = client.get(reverse("landing"))
        assert "analytics/landing.html" in [t.name for t in response.templates]

    def test_authenticated_redirects_to_dashboard(self, client, db):
        user = create_user()
        client.force_login(user)
        response = client.get(reverse("landing"))
        assert response.status_code == 302
        assert "/dashboard/" in response["Location"]


# ═════════════════════════════════════════════════════════════════════════════
# Dashboard View
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.django_db
class TestDashboardViewAuthentication:
    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get(reverse("dashboard"))
        assert response.status_code == 302
        assert "/accounts/" in response["Location"] or "login" in response["Location"].lower()

    def test_authenticated_returns_200(self, client, db):
        user = create_user()
        client.force_login(user)
        response = client.get(reverse("dashboard"))
        assert response.status_code == 200

    def test_dashboard_uses_correct_template(self, client, db):
        user = create_user()
        client.force_login(user)
        response = client.get(reverse("dashboard"))
        assert "analytics/dashboard.html" in [t.name for t in response.templates]


@pytest.mark.integration
@pytest.mark.django_db
class TestDashboardContextKeys:
    """Context must contain all keys consumed by the template."""

    def setup_method(self):
        self.client = Client()
        self.user = create_user("ctx_user")
        self.client.force_login(self.user)
        create_event(self.user, lines_added=50, errors=2)

    EXPECTED_KEYS = [
        "api_token",
        "total_events",
        "total_additions",
        "total_deletions",
        "total_active_time",
        "total_idle_time",
        "total_time",
        "projects_json",
        "languages_json",
        "avg_stress",
        "stress_level",
        "stress_color",
        "total_builds",
        "total_failures",
        "stress_breakdown_json",
    ]

    def test_all_context_keys_present(self):
        response = self.client.get(reverse("dashboard"))
        for key in self.EXPECTED_KEYS:
            assert key in response.context, f"Missing context key: {key}"

    def test_total_events_counts_correctly(self):
        create_event(self.user)  # add a second event
        response = self.client.get(reverse("dashboard"))
        assert response.context["total_events"] == 2

    def test_total_additions_sums_correctly(self):
        # setup_method created 1 event with lines_added=50
        response = self.client.get(reverse("dashboard"))
        assert response.context["total_additions"] == 50

    def test_projects_json_is_valid_json(self):
        response = self.client.get(reverse("dashboard"))
        try:
            data = json.loads(response.context["projects_json"])
            assert isinstance(data, list)
        except json.JSONDecodeError:
            pytest.fail("projects_json is not valid JSON")

    def test_languages_json_is_valid_json(self):
        response = self.client.get(reverse("dashboard"))
        try:
            data = json.loads(response.context["languages_json"])
            assert isinstance(data, list)
        except json.JSONDecodeError:
            pytest.fail("languages_json is not valid JSON")

    def test_stress_breakdown_json_is_valid_json(self):
        response = self.client.get(reverse("dashboard"))
        try:
            data = json.loads(response.context["stress_breakdown_json"])
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail("stress_breakdown_json is not valid JSON")


@pytest.mark.integration
@pytest.mark.django_db
class TestDashboardStressThresholds:
    """Verify stress_level classification matches thresholds in views.py."""

    def _get_stress_context(self, stress_kwargs):
        c = Client()
        user = create_user(f"stress_{stress_kwargs.get('errors', 0)}")
        c.force_login(user)
        create_event(user, **stress_kwargs)
        return c.get(reverse("dashboard")).context

    def test_zero_stress_is_low(self):
        ctx = self._get_stress_context({})
        assert ctx["stress_level"] == "Low"
        assert ctx["stress_color"] == "emerald"

    def test_stress_score_30_is_low(self):
        # errors=10 → raw=30; total_events=1; avg=30.0 → Low
        ctx = self._get_stress_context({"errors": 10})
        assert ctx["avg_stress"] == 30.0
        assert ctx["stress_level"] == "Low"

    def test_stress_score_31_is_medium(self):
        # errors=11 → raw=33; avg=33 → Medium (raw/1 event=33)
        ctx = self._get_stress_context({"errors": 11})
        assert ctx["avg_stress"] > 30
        assert ctx["stress_level"] == "Medium"
        assert ctx["stress_color"] == "yellow"

    def test_stress_score_60_is_medium(self):
        # repeated_errors=12 → raw=60; avg=60 → Medium
        ctx = self._get_stress_context({"repeated_errors": 12})
        assert ctx["avg_stress"] == 60.0
        assert ctx["stress_level"] == "Medium"

    def test_stress_score_61_is_high(self):
        # repeated_errors=13 → raw=65; avg=65 → High
        ctx = self._get_stress_context({"repeated_errors": 13})
        assert ctx["avg_stress"] > 60
        assert ctx["stress_level"] == "High"
        assert ctx["stress_color"] == "red"

    def test_no_events_avg_stress_is_zero(self):
        """With no events, avg_stress must be 0 (division-by-zero guard)."""
        c = Client()
        user = create_user("noevents")
        c.force_login(user)
        ctx = c.get(reverse("dashboard")).context
        assert ctx["avg_stress"] == 0
        assert ctx["stress_level"] == "Low"

    def test_avg_stress_capped_at_100(self):
        """avg_stress value is never greater than 100."""
        ctx = self._get_stress_context({
            "errors": 100,
            "repeated_errors": 100,
            "build_failures": 100,
            "terminal_errors": 100,
        })
        assert ctx["avg_stress"] <= 100


@pytest.mark.integration
@pytest.mark.django_db
class TestDashboardFmtTime:
    """Test that time display strings are formatted correctly."""

    def _get_time_ctx(self, active_secs, idle_secs):
        c = Client()
        user = create_user(f"timefmt_{active_secs}")
        c.force_login(user)
        create_event(user, active_seconds=active_secs, idle_seconds=idle_secs)
        return c.get(reverse("dashboard")).context

    def test_active_time_minutes_format(self):
        ctx = self._get_time_ctx(active_secs=180, idle_secs=0)
        assert ctx["total_active_time"] == "3m 0s"

    def test_active_time_hours_format(self):
        ctx = self._get_time_ctx(active_secs=3661, idle_secs=0)
        # 1h 1m
        assert "h" in ctx["total_active_time"]
        assert "m" in ctx["total_active_time"]

    def test_total_time_sums_active_and_idle(self):
        ctx = self._get_time_ctx(active_secs=60, idle_secs=60)
        # total = 120s = 2m 0s
        assert ctx["total_time"] == "2m 0s"


# ═════════════════════════════════════════════════════════════════════════════
# Stats View
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.django_db
class TestStatsView:
    def test_unauthenticated_redirects(self, client):
        response = client.get(reverse("stats"))
        assert response.status_code == 302

    def test_authenticated_returns_200(self, client, db):
        user = create_user("statsuser")
        client.force_login(user)
        response = client.get(reverse("stats"))
        assert response.status_code == 200

    def test_stats_template_used(self, client, db):
        user = create_user("statstempl")
        client.force_login(user)
        response = client.get(reverse("stats"))
        assert "analytics/stats.html" in [t.name for t in response.templates]

    def test_events_in_context(self, client, db):
        user = create_user("statsevents")
        client.force_login(user)
        create_event(user)
        create_event(user, language="JavaScript")
        response = client.get(reverse("stats"))
        assert len(response.context["events"]) == 2

    def test_events_limited_to_50(self, client, db):
        user = create_user("stats50")
        client.force_login(user)
        for _ in range(60):
            create_event(user)
        response = client.get(reverse("stats"))
        assert len(response.context["events"]) == 50

    def test_events_belong_to_current_user_only(self, client, db):
        user1 = create_user("statsu1")
        user2 = create_user("statsu2")
        create_event(user1)
        create_event(user2)  # should NOT appear for user1
        client.force_login(user1)
        response = client.get(reverse("stats"))
        for event in response.context["events"]:
            assert event.user == user1


# ═════════════════════════════════════════════════════════════════════════════
# About View
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.django_db
class TestAboutView:
    def test_unauthenticated_redirects(self, client):
        response = client.get(reverse("about"))
        assert response.status_code == 302

    def test_authenticated_returns_200(self, client, db):
        user = create_user("aboutuser")
        client.force_login(user)
        response = client.get(reverse("about"))
        assert response.status_code == 200

    def test_about_template_used(self, client, db):
        user = create_user("abouttempl")
        client.force_login(user)
        response = client.get(reverse("about"))
        assert "analytics/about.html" in [t.name for t in response.templates]

"""
telemetry/tests/test_django_testcase.py
════════════════════════════════════════
Django TestCase-style tests for the scoring engine and API layer.

These tests use Django's built-in TestCase class (unittest.TestCase subclass)
rather than pytest fixtures, demonstrating compatibility with both testing
approaches. They are discovered by both `pytest` and `python manage.py test`.

TestCase classes use a transaction rollback strategy – each test is wrapped
in a transaction that is rolled back on teardown.

Coverage
────────
* HeartbeatAPI CRUD lifecycle (Create → Read → Update indirectly → Delete)
* Scoring engine (stress_score) correctness via Django TestCase assertions
* UserProfile form validation via Django TestCase
* Dashboard view context assertions
* Authentication boundary checks
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from telemetry.models import TelemetryEvent, UserProfile
from telemetry.serializers import TelemetryEventSerializer
from telemetry.forms import UserProfileForm

HEARTBEAT_URL = "/api/heartbeats/"

VALID_PAYLOAD = {
    "language": "Python",
    "project_name": "ACLAS_DjangoTC",
    "lines_added": 5,
    "lines_deleted": 1,
    "active_seconds": 60,
    "idle_seconds": 15,
}


# ═════════════════════════════════════════════════════════════════════════════
# Scoring Engine – Django TestCase
# ═════════════════════════════════════════════════════════════════════════════

class ScoringEngineTestCase(TestCase):
    """Verifies the TelemetryEvent.stress_score weighted formula using
    Django TestCase (unittest-style assertions)."""

    def setUp(self):
        self.user = User.objects.create_user("scorer", password="pass123")

    def _make(self, **kwargs):
        defaults = dict(
            user=self.user, language="Py", project_name="P",
        )
        defaults.update(kwargs)
        return TelemetryEvent(**defaults)

    # ── Weights ─────────────────────────────────────────────────────────────

    def test_errors_weight_is_3(self):
        e = self._make(errors=1)
        self.assertEqual(e.stress_score, 3)

    def test_repeated_errors_weight_is_5(self):
        e = self._make(repeated_errors=1)
        self.assertEqual(e.stress_score, 5)

    def test_build_failures_weight_is_4(self):
        e = self._make(build_failures=1)
        self.assertEqual(e.stress_score, 4)

    def test_file_switches_weight_is_1(self):
        e = self._make(file_switches=1)
        self.assertEqual(e.stress_score, 1)

    def test_undo_count_weight_is_2(self):
        e = self._make(undo_count=1)
        self.assertEqual(e.stress_score, 2)

    def test_terminal_errors_weight_is_3(self):
        e = self._make(terminal_errors=1)
        self.assertEqual(e.stress_score, 3)

    def test_build_runs_weight_is_0(self):
        """build_runs should contribute 0 to stress_score."""
        e = self._make(build_runs=999)
        self.assertEqual(e.stress_score, 0)

    # ── Additive ─────────────────────────────────────────────────────────────

    def test_all_metrics_combined(self):
        # 2*3 + 1*5 + 1*4 + 3*1 + 2*2 + 1*3 = 6+5+4+3+4+3 = 25
        e = self._make(
            errors=2, repeated_errors=1, build_failures=1,
            file_switches=3, undo_count=2, terminal_errors=1,
        )
        self.assertEqual(e.stress_score, 25)

    # ── Clamping ─────────────────────────────────────────────────────────────

    def test_score_never_exceeds_100(self):
        e = self._make(
            errors=50, repeated_errors=50, build_failures=50,
            file_switches=50, undo_count=50, terminal_errors=50,
        )
        self.assertLessEqual(e.stress_score, 100)

    def test_score_exactly_100(self):
        e = self._make(repeated_errors=20)  # 20 * 5 = 100
        self.assertEqual(e.stress_score, 100)

    def test_zero_inputs_give_zero_score(self):
        e = self._make()
        self.assertEqual(e.stress_score, 0)


# ═════════════════════════════════════════════════════════════════════════════
# Heartbeat API – CRUD lifecycle (Django TestCase)
# ═════════════════════════════════════════════════════════════════════════════

class HeartbeatAPITestCase(TestCase):
    """Full CRUD lifecycle of TelemetryEvent via API, using Django TestCase."""

    def setUp(self):
        self.user = User.objects.create_user("hb_tc_user", password="pass123")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    # ── Create (POST) ────────────────────────────────────────────────────────

    def test_create_event_returns_201(self):
        response = self.client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        self.assertEqual(response.status_code, 201)

    def test_create_event_persists_to_db(self):
        self.client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        self.assertEqual(TelemetryEvent.objects.filter(user=self.user).count(), 1)

    def test_create_event_stores_correct_language(self):
        self.client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        event = TelemetryEvent.objects.get(user=self.user)
        self.assertEqual(event.language, "Python")

    def test_create_event_stores_correct_project(self):
        self.client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        event = TelemetryEvent.objects.get(user=self.user)
        self.assertEqual(event.project_name, "ACLAS_DjangoTC")

    def test_create_event_with_full_stress_payload(self):
        payload = {
            **VALID_PAYLOAD,
            "errors": 3, "repeated_errors": 2, "build_failures": 1,
            "file_switches": 4, "undo_count": 2, "terminal_errors": 1,
        }
        response = self.client.post(HEARTBEAT_URL, data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        event = TelemetryEvent.objects.get(user=self.user)
        self.assertEqual(event.errors, 3)
        self.assertEqual(event.repeated_errors, 2)

    # ── Read (via ORM) ───────────────────────────────────────────────────────

    def test_read_event_from_db(self):
        TelemetryEvent.objects.create(user=self.user, language="Go", project_name="GoProj")
        event = TelemetryEvent.objects.get(user=self.user, language="Go")
        self.assertEqual(event.project_name, "GoProj")

    def test_filter_events_by_project(self):
        TelemetryEvent.objects.create(user=self.user, language="Python", project_name="A")
        TelemetryEvent.objects.create(user=self.user, language="Python", project_name="B")
        events = TelemetryEvent.objects.filter(user=self.user, project_name="A")
        self.assertEqual(events.count(), 1)

    # ── Update (via ORM) ─────────────────────────────────────────────────────

    def test_update_event_language(self):
        event = TelemetryEvent.objects.create(
            user=self.user, language="JavaScript", project_name="JS"
        )
        event.language = "TypeScript"
        event.save()
        refreshed = TelemetryEvent.objects.get(pk=event.pk)
        self.assertEqual(refreshed.language, "TypeScript")

    def test_update_stress_fields(self):
        event = TelemetryEvent.objects.create(
            user=self.user, language="Python", project_name="Upd"
        )
        event.errors = 10
        event.save()
        refreshed = TelemetryEvent.objects.get(pk=event.pk)
        self.assertEqual(refreshed.errors, 10)

    # ── Delete (via ORM) ─────────────────────────────────────────────────────

    def test_delete_event(self):
        event = TelemetryEvent.objects.create(
            user=self.user, language="Python", project_name="Del"
        )
        pk = event.pk
        event.delete()
        self.assertFalse(TelemetryEvent.objects.filter(pk=pk).exists())

    def test_delete_user_cascades_events(self):
        TelemetryEvent.objects.create(user=self.user, language="Python", project_name="Cascade")
        user_pk = self.user.pk
        self.user.delete()
        self.assertEqual(TelemetryEvent.objects.filter(user_id=user_pk).count(), 0)

    # ── Authentication ───────────────────────────────────────────────────────

    def test_unauthenticated_post_returns_401(self):
        anon_client = APIClient()
        response = anon_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        self.assertEqual(response.status_code, 401)

    def test_invalid_payload_returns_400(self):
        bad = {k: v for k, v in VALID_PAYLOAD.items() if k != "language"}
        response = self.client.post(HEARTBEAT_URL, data=bad, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("language", response.data)


# ═════════════════════════════════════════════════════════════════════════════
# UserProfile Form – Django TestCase
# ═════════════════════════════════════════════════════════════════════════════

class UserProfileFormTestCase(TestCase):
    """Form validation tests using Django TestCase."""

    def test_valid_display_name_accepted(self):
        form = UserProfileForm(data={"display_name": "Alice"})
        self.assertTrue(form.is_valid())

    def test_admin_name_rejected(self):
        form = UserProfileForm(data={"display_name": "admin"})
        self.assertFalse(form.is_valid())
        self.assertIn("display_name", form.errors)

    def test_admin_case_insensitive_rejection(self):
        for name in ["Admin", "ADMIN", "aDmIn"]:
            with self.subTest(name=name):
                form = UserProfileForm(data={"display_name": name})
                self.assertFalse(form.is_valid())

    def test_short_name_rejected(self):
        form = UserProfileForm(data={"display_name": "AB"})
        self.assertFalse(form.is_valid())
        self.assertIn("display_name", form.errors)

    def test_exactly_3_chars_accepted(self):
        form = UserProfileForm(data={"display_name": "ABC"})
        self.assertTrue(form.is_valid())

    def test_preferred_language_optional(self):
        form = UserProfileForm(data={"display_name": "Alice"})
        self.assertTrue(form.is_valid())


# ═════════════════════════════════════════════════════════════════════════════
# Dashboard – Django TestCase
# ═════════════════════════════════════════════════════════════════════════════

class DashboardViewTestCase(TestCase):
    """Dashboard integration tests using Django TestCase + Django test Client."""

    def setUp(self):
        self.user = User.objects.create_user("dash_tc_user", password="pass123")
        self.client.force_login(self.user)

    def _create_event(self, **kwargs):
        defaults = dict(language="Python", project_name="TC_Proj",
                        lines_added=10, errors=0)
        defaults.update(kwargs)
        return TelemetryEvent.objects.create(user=self.user, **defaults)

    def test_dashboard_returns_200(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_context_has_total_events(self):
        self._create_event()
        self._create_event()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_events"], 2)

    def test_dashboard_no_events_avg_stress_zero(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["avg_stress"], 0)

    def test_dashboard_low_stress_label(self):
        self._create_event(errors=2)  # score = 6 per event → avg=6 → Low
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["stress_level"], "Low")

    def test_dashboard_high_stress_label(self):
        # repeated_errors=14 → raw=70 → avg=70 → High
        self._create_event(repeated_errors=14)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["stress_level"], "High")

    def test_unauthenticated_dashboard_redirects(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_projects_json_is_a_list(self):
        import json
        self._create_event()
        response = self.client.get(reverse("dashboard"))
        data = json.loads(response.context["projects_json"])
        self.assertIsInstance(data, list)

    def test_languages_json_is_a_list(self):
        import json
        self._create_event()
        response = self.client.get(reverse("dashboard"))
        data = json.loads(response.context["languages_json"])
        self.assertIsInstance(data, list)

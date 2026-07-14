"""
telemetry/tests/test_models.py
══════════════════════════════
Unit tests for TelemetryEvent and UserProfile models.

Coverage goals
──────────────
* stress_score property: boundary values (0, 30, 60, 100+)
* stress_score clamping at 100
* Default field values
* __str__ representations
* UserProfile OneToOne constraint

Markers: @pytest.mark.unit  (no HTTP, no network)
"""
import pytest
from django.contrib.auth.models import User
from telemetry.models import TelemetryEvent, UserProfile


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

def make_event(user, **kwargs) -> TelemetryEvent:
    """Factory helper – creates an unsaved TelemetryEvent instance."""
    defaults = dict(
        language="Python",
        project_name="Test",
        lines_added=0,
        lines_deleted=0,
        active_seconds=0,
        idle_seconds=0,
    )
    defaults.update(kwargs)
    return TelemetryEvent(user=user, **defaults)


# ═════════════════════════════════════════════════════════════════════════════
# TelemetryEvent – stress_score property
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestStressScoreCalculation:
    """Verifies the weighted stress formula and boundary clamp."""

    def test_zero_stress_with_no_signals(self, user):
        """All stress fields at zero → score is 0."""
        event = make_event(user)
        assert event.stress_score == 0

    def test_formula_weights_are_correct(self, user):
        """
        Validate the weight coefficients documented in the model:
          errors x 3, repeated_errors x 5, build_failures x 4,
          file_switches x 1, undo_count x 2, terminal_errors x 3
        """
        event = make_event(
            user,
            errors=1,           # +3
            repeated_errors=1,  # +5
            build_failures=1,   # +4
            file_switches=1,    # +1
            undo_count=1,       # +2
            terminal_errors=1,  # +3
        )
        expected = 3 + 5 + 4 + 1 + 2 + 3  # = 18
        assert event.stress_score == expected

    def test_score_clamped_at_100(self, user):
        """Very high stress values must not exceed 100."""
        event = make_event(
            user,
            errors=100,
            repeated_errors=100,
            build_failures=100,
            file_switches=100,
            undo_count=100,
            terminal_errors=100,
        )
        assert event.stress_score == 100

    def test_score_exactly_at_100_boundary(self, user):
        """Score equal to exactly 100 is not clamped or altered."""
        # repeated_errors x 5 = 20, so 20 repeated errors = 100
        event = make_event(user, repeated_errors=20)
        assert event.stress_score == 100

    def test_score_below_100_not_clamped(self, user):
        """Score of 99 is returned as-is."""
        # errors x 3 = 99 -> errors = 33
        event = make_event(user, errors=33)
        assert event.stress_score == 99

    def test_only_errors_contribute(self, user):
        """Isolated: only errors field, other stress fields zero."""
        event = make_event(user, errors=5)
        assert event.stress_score == 5 * 3  # = 15

    def test_only_repeated_errors_contribute(self, user):
        event = make_event(user, repeated_errors=3)
        assert event.stress_score == 3 * 5  # = 15

    def test_only_build_failures_contribute(self, user):
        event = make_event(user, build_failures=4)
        assert event.stress_score == 4 * 4  # = 16

    def test_only_file_switches_contribute(self, user):
        event = make_event(user, file_switches=7)
        assert event.stress_score == 7 * 1  # = 7

    def test_only_undo_count_contributes(self, user):
        event = make_event(user, undo_count=6)
        assert event.stress_score == 6 * 2  # = 12

    def test_only_terminal_errors_contribute(self, user):
        event = make_event(user, terminal_errors=4)
        assert event.stress_score == 4 * 3  # = 12

    def test_build_runs_does_not_affect_score(self, user):
        """build_runs is NOT part of the stress formula; only build_failures is."""
        event_with_runs = make_event(user, build_runs=100)
        event_without = make_event(user)
        assert event_with_runs.stress_score == event_without.stress_score == 0


# ═════════════════════════════════════════════════════════════════════════════
# TelemetryEvent – default field values (requires DB)
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.django_db
class TestTelemetryEventDefaults:
    """Persisted default values must match the model definition."""

    def test_default_stress_fields_are_zero(self, user):
        event = TelemetryEvent.objects.create(
            user=user,
            language="Python",
            project_name="Defaults",
        )
        assert event.errors == 0
        assert event.repeated_errors == 0
        assert event.build_runs == 0
        assert event.build_failures == 0
        assert event.file_switches == 0
        assert event.undo_count == 0
        assert event.terminal_errors == 0

    def test_default_code_metrics_are_zero(self, user):
        event = TelemetryEvent.objects.create(
            user=user,
            language="Python",
            project_name="Defaults",
        )
        assert event.lines_added == 0
        assert event.lines_deleted == 0
        assert event.active_seconds == 0
        assert event.idle_seconds == 0

    def test_file_defaults_to_empty_string(self, user):
        event = TelemetryEvent.objects.create(
            user=user,
            language="Python",
            project_name="Defaults",
        )
        assert event.file == ""

    def test_received_at_is_set_automatically(self, user):
        event = TelemetryEvent.objects.create(
            user=user,
            language="Python",
            project_name="AutoTime",
        )
        assert event.received_at is not None

    def test_timestamp_defaults_to_now(self, user):
        from django.utils import timezone
        before = timezone.now()
        event = TelemetryEvent.objects.create(
            user=user,
            language="Python",
            project_name="AutoTime",
        )
        after = timezone.now()
        assert before <= event.timestamp <= after


# ═════════════════════════════════════════════════════════════════════════════
# TelemetryEvent – __str__
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.django_db
class TestTelemetryEventStr:
    def test_str_contains_username(self, telemetry_event):
        assert telemetry_event.user.username in str(telemetry_event)

    def test_str_contains_language(self, telemetry_event):
        assert telemetry_event.language in str(telemetry_event)


# ═════════════════════════════════════════════════════════════════════════════
# UserProfile – model constraints
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.django_db
class TestUserProfile:
    def test_profile_str(self, user):
        profile = UserProfile.objects.create(user=user, display_name="Dev One")
        assert user.username in str(profile)

    def test_profile_one_to_one_constraint(self, user):
        """Creating a second profile for the same user must raise IntegrityError."""
        from django.db import IntegrityError
        UserProfile.objects.create(user=user, display_name="First")
        with pytest.raises(IntegrityError):
            UserProfile.objects.create(user=user, display_name="Second")

    def test_profile_optional_preferred_language(self, user):
        profile = UserProfile.objects.create(user=user, display_name="Dev")
        assert profile.preferred_language is None

    def test_profile_preferred_language_saved(self, user):
        profile = UserProfile.objects.create(
            user=user, display_name="Dev", preferred_language="Python"
        )
        assert profile.preferred_language == "Python"

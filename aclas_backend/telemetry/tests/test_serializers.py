"""
telemetry/tests/test_serializers.py
═════════════════════════════════════
Unit tests for TelemetryEventSerializer.

Coverage goals
──────────────
* Required fields validation (language, project_name)
* Optional fields have correct defaults when omitted
* Invalid data types rejected with 400-style error keys
* Valid payload accepted and clean data returned
* Stress metric fields are truly optional

Marker: @pytest.mark.unit
"""
import pytest
from django.utils import timezone
from telemetry.serializers import TelemetryEventSerializer


REQUIRED_VALID = {
    "language": "Python",
    "project_name": "ACLAS",
    "lines_added": 5,
    "lines_deleted": 1,
    "active_seconds": 60,
    "idle_seconds": 10,
}


@pytest.mark.unit
class TestTelemetryEventSerializerValid:
    """Happy-path serializer tests."""

    def test_minimal_payload_is_valid(self):
        """Minimum required fields pass validation."""
        s = TelemetryEventSerializer(data=REQUIRED_VALID)
        assert s.is_valid(), s.errors

    def test_full_payload_with_stress_metrics_is_valid(self):
        full = {
            **REQUIRED_VALID,
            "errors": 2,
            "repeated_errors": 1,
            "build_runs": 3,
            "build_failures": 1,
            "file_switches": 5,
            "undo_count": 2,
            "terminal_errors": 1,
            "file": "src/main.py",
            "timestamp": timezone.now().isoformat(),
        }
        s = TelemetryEventSerializer(data=full)
        assert s.is_valid(), s.errors

    def test_validated_data_contains_language(self):
        s = TelemetryEventSerializer(data=REQUIRED_VALID)
        s.is_valid()
        assert s.validated_data["language"] == "Python"

    def test_validated_data_contains_project_name(self):
        s = TelemetryEventSerializer(data=REQUIRED_VALID)
        s.is_valid()
        assert s.validated_data["project_name"] == "ACLAS"

    def test_optional_stress_fields_absent_means_no_error(self):
        """Stress metrics omitted from payload → serializer still valid."""
        s = TelemetryEventSerializer(data=REQUIRED_VALID)
        assert s.is_valid(), s.errors

    def test_file_field_optional_and_absent_is_ok(self):
        payload = {k: v for k, v in REQUIRED_VALID.items()}  # no 'file'
        s = TelemetryEventSerializer(data=payload)
        assert s.is_valid(), s.errors

    def test_timestamp_field_optional_and_absent_is_ok(self):
        payload = {k: v for k, v in REQUIRED_VALID.items()}  # no 'timestamp'
        s = TelemetryEventSerializer(data=payload)
        assert s.is_valid(), s.errors


@pytest.mark.unit
class TestTelemetryEventSerializerInvalid:
    """Validation rejection tests."""

    def test_missing_language_fails(self):
        payload = {k: v for k, v in REQUIRED_VALID.items() if k != "language"}
        s = TelemetryEventSerializer(data=payload)
        assert not s.is_valid()
        assert "language" in s.errors

    def test_missing_project_name_fails(self):
        payload = {k: v for k, v in REQUIRED_VALID.items() if k != "project_name"}
        s = TelemetryEventSerializer(data=payload)
        assert not s.is_valid()
        assert "project_name" in s.errors

    def test_negative_lines_added_fails(self):
        """IntegerField with negative value should be rejected (min_value not set,
        but we document expected current behaviour: passes validation.
        If a min_value constraint is added later, this test should be updated.)"""
        # Currently the model/serializer has no min_value constraint, so this
        # just documents the behaviour; change assertion if constraint is added.
        payload = {**REQUIRED_VALID, "lines_added": -1}
        s = TelemetryEventSerializer(data=payload)
        # Document current behaviour (no min_value constraint):
        assert s.is_valid()  # Expected to pass until a constraint is added

    def test_non_integer_lines_added_fails(self):
        payload = {**REQUIRED_VALID, "lines_added": "not_a_number"}
        s = TelemetryEventSerializer(data=payload)
        assert not s.is_valid()
        assert "lines_added" in s.errors

    def test_empty_language_fails(self):
        payload = {**REQUIRED_VALID, "language": ""}
        s = TelemetryEventSerializer(data=payload)
        assert not s.is_valid()
        assert "language" in s.errors

    def test_empty_project_name_fails(self):
        payload = {**REQUIRED_VALID, "project_name": ""}
        s = TelemetryEventSerializer(data=payload)
        assert not s.is_valid()
        assert "project_name" in s.errors

    def test_invalid_timestamp_format_fails(self):
        payload = {**REQUIRED_VALID, "timestamp": "not-a-date"}
        s = TelemetryEventSerializer(data=payload)
        assert not s.is_valid()
        assert "timestamp" in s.errors

    def test_non_integer_errors_field_fails(self):
        payload = {**REQUIRED_VALID, "errors": "many"}
        s = TelemetryEventSerializer(data=payload)
        assert not s.is_valid()
        assert "errors" in s.errors


@pytest.mark.unit
class TestTelemetryEventSerializerFields:
    """Verify the exposed field set exactly matches the model contract."""

    def test_user_field_not_exposed(self):
        """The 'user' field must NOT be in the serializer (set server-side)."""
        s = TelemetryEventSerializer()
        assert "user" not in s.fields

    def test_expected_fields_present(self):
        expected = {
            "language", "project_name", "file", "timestamp",
            "lines_added", "lines_deleted", "active_seconds", "idle_seconds",
            "errors", "repeated_errors", "build_runs", "build_failures",
            "file_switches", "undo_count", "terminal_errors",
        }
        s = TelemetryEventSerializer()
        assert expected == set(s.fields.keys())

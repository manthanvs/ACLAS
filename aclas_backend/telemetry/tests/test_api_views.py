"""
telemetry/tests/test_api_views.py
══════════════════════════════════
Integration tests for the HeartbeatAPIView (POST /api/heartbeats/).

Coverage goals
──────────────
* Authentication: anonymous request → 401
* Authentication: wrong/invalid token → 401
* Valid minimal payload → 201, event persisted in DB
* Valid full payload with stress metrics → 201
* Missing required field → 400
* Invalid field type → 400
* Event is associated with the authenticated user
* Stress fields default to 0 when omitted
* Multiple heartbeats accumulate correctly

Marker: @pytest.mark.integration
"""
import pytest
from django.urls import reverse
from rest_framework import status
from telemetry.models import TelemetryEvent

HEARTBEAT_URL = "/api/heartbeats/"

VALID_PAYLOAD = {
    "language": "Python",
    "project_name": "ACLAS_Test",
    "lines_added": 10,
    "lines_deleted": 2,
    "active_seconds": 120,
    "idle_seconds": 30,
}


@pytest.mark.integration
@pytest.mark.django_db
class TestHeartbeatAuthentication:
    """Unauthenticated and bad-token requests must be rejected."""

    def test_anonymous_request_returns_401(self, api_client):
        response = api_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_returns_401(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Token invalidtoken123abc")
        response = api_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_method_not_allowed(self, authed_client):
        """GET on /api/heartbeats/ should return 405 Method Not Allowed."""
        response = authed_client.get(HEARTBEAT_URL)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.integration
@pytest.mark.django_db
class TestHeartbeatSuccess:
    """Authenticated valid requests must be persisted and return 201."""

    def test_valid_minimal_payload_returns_201(self, authed_client):
        response = authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_response_body_has_status_key(self, authed_client):
        response = authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        assert "status" in response.data

    def test_response_body_status_value(self, authed_client):
        response = authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        assert response.data["status"] == "Heartbeat recorded"

    def test_event_persisted_in_database(self, authed_client, user):
        before = TelemetryEvent.objects.filter(user=user).count()
        authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        after = TelemetryEvent.objects.filter(user=user).count()
        assert after == before + 1

    def test_event_belongs_to_authenticated_user(self, authed_client, user):
        authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        event = TelemetryEvent.objects.filter(user=user).last()
        assert event is not None
        assert event.user == user

    def test_event_language_stored_correctly(self, authed_client, user):
        authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        event = TelemetryEvent.objects.filter(user=user).last()
        assert event.language == "Python"

    def test_event_project_name_stored_correctly(self, authed_client, user):
        authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        event = TelemetryEvent.objects.filter(user=user).last()
        assert event.project_name == "ACLAS_Test"

    def test_valid_full_payload_with_stress_metrics(self, authed_client, user, stress_event_payload):
        response = authed_client.post(HEARTBEAT_URL, data=stress_event_payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        event = TelemetryEvent.objects.filter(user=user).last()
        assert event.errors == stress_event_payload["errors"]
        assert event.repeated_errors == stress_event_payload["repeated_errors"]
        assert event.build_failures == stress_event_payload["build_failures"]

    def test_stress_fields_default_to_zero_when_absent(self, authed_client, user):
        """Omitting all stress fields → DB stores zeros, not null."""
        authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        event = TelemetryEvent.objects.filter(user=user).last()
        assert event.errors == 0
        assert event.repeated_errors == 0
        assert event.build_failures == 0
        assert event.file_switches == 0
        assert event.undo_count == 0
        assert event.terminal_errors == 0

    def test_multiple_heartbeats_accumulate(self, authed_client, user):
        for _ in range(3):
            authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        assert TelemetryEvent.objects.filter(user=user).count() == 3

    def test_file_field_stored_when_provided(self, authed_client, user):
        payload = {**VALID_PAYLOAD, "file": "src/main.py"}
        authed_client.post(HEARTBEAT_URL, data=payload, format="json")
        event = TelemetryEvent.objects.filter(user=user).last()
        assert event.file == "src/main.py"

    def test_file_field_empty_string_when_omitted(self, authed_client, user):
        authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        event = TelemetryEvent.objects.filter(user=user).last()
        assert event.file == ""


@pytest.mark.integration
@pytest.mark.django_db
class TestHeartbeatValidationErrors:
    """Invalid payloads must be rejected with HTTP 400."""

    def test_missing_language_returns_400(self, authed_client):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "language"}
        response = authed_client.post(HEARTBEAT_URL, data=payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "language" in response.data

    def test_missing_project_name_returns_400(self, authed_client):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "project_name"}
        response = authed_client.post(HEARTBEAT_URL, data=payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "project_name" in response.data

    def test_non_integer_lines_added_returns_400(self, authed_client):
        payload = {**VALID_PAYLOAD, "lines_added": "not_a_number"}
        response = authed_client.post(HEARTBEAT_URL, data=payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "lines_added" in response.data

    def test_invalid_timestamp_returns_400(self, authed_client):
        payload = {**VALID_PAYLOAD, "timestamp": "invalid-date"}
        response = authed_client.post(HEARTBEAT_URL, data=payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "timestamp" in response.data

    def test_bad_request_does_not_create_event(self, authed_client, user):
        """Invalid payload must not create any DB record."""
        before = TelemetryEvent.objects.filter(user=user).count()
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "language"}
        authed_client.post(HEARTBEAT_URL, data=payload, format="json")
        after = TelemetryEvent.objects.filter(user=user).count()
        assert after == before


@pytest.mark.integration
@pytest.mark.django_db
class TestHeartbeatUserIsolation:
    """Events of one user must not bleed into another user's records."""

    def test_events_isolated_by_user(self, authed_client, user, db):
        from django.contrib.auth.models import User
        from rest_framework.authtoken.models import Token
        from rest_framework.test import APIClient

        other_user = User.objects.create_user(username="other", password="pass")
        other_token, _ = Token.objects.get_or_create(user=other_user)
        other_client = APIClient()
        other_client.credentials(HTTP_AUTHORIZATION=f"Token {other_token.key}")

        authed_client.post(HEARTBEAT_URL, data=VALID_PAYLOAD, format="json")
        other_client.post(HEARTBEAT_URL, data={**VALID_PAYLOAD, "project_name": "OtherProject"}, format="json")

        assert TelemetryEvent.objects.filter(user=user).count() == 1
        assert TelemetryEvent.objects.filter(user=other_user).count() == 1

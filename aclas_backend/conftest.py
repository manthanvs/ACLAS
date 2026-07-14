"""
conftest.py – Shared pytest fixtures for the ACLAS backend test suite.

Scope ladder:
  session  → DB-safe objects reused across all tests in a session
  function → fresh object per test (default)
"""
import pytest
from django.contrib.auth.models import User, Group
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from telemetry.models import TelemetryEvent, UserProfile


# ─────────────────────────────────────────────────────────────────────────────
# User fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    """A regular authenticated user."""
    u = User.objects.create_user(
        username="testdev",
        email="dev@aclas.test",
        password="Str0ng!Pass",
    )
    return u


@pytest.fixture
def manager_user(db):
    """A user that belongs to the 'Manager' group."""
    group, _ = Group.objects.get_or_create(name="Manager")
    u = User.objects.create_user(
        username="manager",
        email="manager@aclas.test",
        password="Str0ng!Pass",
    )
    u.groups.add(group)
    return u


@pytest.fixture
def auth_token(user):
    """DRF auth token for *user*."""
    token, _ = Token.objects.get_or_create(user=user)
    return token


@pytest.fixture
def api_client():
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def authed_client(api_client, auth_token):
    """DRF test client pre-authenticated with *user*'s token."""
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {auth_token.key}")
    return api_client


# ─────────────────────────────────────────────────────────────────────────────
# TelemetryEvent fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def base_event_payload():
    """Minimum valid heartbeat payload (no stress metrics)."""
    return {
        "language": "Python",
        "project_name": "ACLAS_Test",
        "lines_added": 10,
        "lines_deleted": 2,
        "active_seconds": 120,
        "idle_seconds": 30,
    }


@pytest.fixture
def stress_event_payload(base_event_payload):
    """Heartbeat payload that includes all stress metric fields."""
    return {
        **base_event_payload,
        "errors": 4,
        "repeated_errors": 2,
        "build_runs": 3,
        "build_failures": 1,
        "file_switches": 5,
        "undo_count": 3,
        "terminal_errors": 2,
    }


@pytest.fixture
def telemetry_event(user):
    """A persisted TelemetryEvent with known stress data."""
    return TelemetryEvent.objects.create(
        user=user,
        language="Python",
        project_name="ACLAS_Test",
        lines_added=10,
        lines_deleted=2,
        active_seconds=120,
        idle_seconds=30,
        errors=2,
        repeated_errors=1,
        build_runs=2,
        build_failures=1,
        file_switches=3,
        undo_count=2,
        terminal_errors=1,
    )

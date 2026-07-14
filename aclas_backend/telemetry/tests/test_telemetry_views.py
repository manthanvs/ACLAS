"""
telemetry/tests/test_telemetry_views.py
════════════════════════════════════════
Integration tests for telemetry template views (settings, manager_dashboard).

Coverage goals
──────────────
* settings_view: unauthenticated → redirect
* settings_view: GET authenticated → 200 with form + api_token context
* settings_view: POST valid form → redirects back to settings
* settings_view: POST invalid form → 200 with form errors
* manager_dashboard: non-manager user → redirect/403
* manager_dashboard: manager group member → 200 with HTML

Marker: @pytest.mark.integration
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from telemetry.models import UserProfile


def create_user(username="teluser", password="pass123"):
    return User.objects.create_user(username=username, password=password)


def create_manager(username="mgr"):
    group, _ = Group.objects.get_or_create(name="Manager")
    user = User.objects.create_user(username=username, password="pass123")
    user.groups.add(group)
    return user


# ═════════════════════════════════════════════════════════════════════════════
# Settings View
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.django_db
class TestSettingsView:
    """Tests for GET/POST of the telemetry settings page."""

    def test_unauthenticated_redirects(self, client):
        response = client.get(reverse("settings"))
        assert response.status_code == 302

    def test_authenticated_get_returns_200(self, client):
        user = create_user("setsvu1")
        client.force_login(user)
        response = client.get(reverse("settings"))
        assert response.status_code == 200

    def test_settings_template_used(self, client):
        user = create_user("setsvu2")
        client.force_login(user)
        response = client.get(reverse("settings"))
        assert "telemetry/settings.html" in [t.name for t in response.templates]

    def test_context_contains_form(self, client):
        user = create_user("setsvu3")
        client.force_login(user)
        response = client.get(reverse("settings"))
        assert "form" in response.context

    def test_context_contains_api_token(self, client):
        user = create_user("setsvu4")
        client.force_login(user)
        response = client.get(reverse("settings"))
        assert "api_token" in response.context
        assert response.context["api_token"] is not None

    def test_profile_created_on_first_get(self, client):
        user = create_user("setsvu5")
        client.force_login(user)
        client.get(reverse("settings"))
        assert UserProfile.objects.filter(user=user).exists()

    def test_post_valid_form_redirects_to_settings(self, client):
        user = create_user("setsvu6")
        client.force_login(user)
        response = client.post(
            reverse("settings"),
            data={"display_name": "DevUser", "preferred_language": "Python"},
        )
        assert response.status_code == 302
        assert "/settings" in response["Location"] or response["Location"] == reverse("settings")

    def test_post_valid_form_saves_display_name(self, client):
        user = create_user("setsvu7")
        client.force_login(user)
        client.post(
            reverse("settings"),
            data={"display_name": "Manthan", "preferred_language": "Python"},
        )
        profile = UserProfile.objects.get(user=user)
        assert profile.display_name == "Manthan"

    def test_post_invalid_form_returns_200(self, client):
        """Invalid data (admin in name) must re-render the form with errors."""
        user = create_user("setsvu8")
        client.force_login(user)
        response = client.post(
            reverse("settings"),
            data={"display_name": "admin"},
        )
        assert response.status_code == 200

    def test_post_invalid_form_shows_errors(self, client):
        user = create_user("setsvu9")
        client.force_login(user)
        response = client.post(
            reverse("settings"),
            data={"display_name": "admin"},
        )
        assert response.context["form"].errors

    def test_post_short_name_fails(self, client):
        user = create_user("setsvu10")
        client.force_login(user)
        response = client.post(
            reverse("settings"),
            data={"display_name": "AB"},
        )
        assert response.status_code == 200
        assert "display_name" in response.context["form"].errors


# ═════════════════════════════════════════════════════════════════════════════
# Manager Dashboard View
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.django_db
class TestManagerDashboardView:
    """Access control for the manager-only dashboard."""

    def test_unauthenticated_redirects(self, client):
        response = client.get(reverse("manager_dashboard"))
        assert response.status_code == 302

    def test_regular_user_denied(self, client):
        """Non-manager authenticated user must be redirected (user_passes_test)."""
        user = create_user("notamgr")
        client.force_login(user)
        response = client.get(reverse("manager_dashboard"))
        # user_passes_test redirects to login (302) when test fails
        assert response.status_code == 302

    def test_manager_user_returns_200(self, client):
        mgr = create_manager("actualmgr")
        client.force_login(mgr)
        response = client.get(reverse("manager_dashboard"))
        assert response.status_code == 200

    def test_manager_dashboard_contains_heading(self, client):
        mgr = create_manager("headingmgr")
        client.force_login(mgr)
        response = client.get(reverse("manager_dashboard"))
        assert b"Manager Dashboard" in response.content

"""
telemetry/tests/test_forms.py
══════════════════════════════
Unit tests for UserProfileForm.

Coverage goals
──────────────
* clean_display_name: 'admin' substring rejection (case-insensitive)
* clean_display_name: minimum length validation (< 3 chars)
* Valid display names are accepted
* preferred_language is optional
* Form saves correctly to UserProfile model

Marker: @pytest.mark.unit
"""
import pytest
from telemetry.forms import UserProfileForm
from telemetry.models import UserProfile


@pytest.mark.unit
class TestUserProfileFormValidDisplayNames:
    """Valid display names must pass form validation."""

    def test_normal_display_name_is_valid(self):
        form = UserProfileForm(data={"display_name": "Alice"})
        assert form.is_valid(), form.errors

    def test_three_character_name_is_valid(self):
        """Boundary: exactly 3 characters should be accepted."""
        form = UserProfileForm(data={"display_name": "Bob"})
        assert form.is_valid(), form.errors

    def test_long_name_is_valid(self):
        form = UserProfileForm(data={"display_name": "VeryLongDisplayNameHere"})
        assert form.is_valid(), form.errors

    def test_name_with_spaces_is_valid(self):
        form = UserProfileForm(data={"display_name": "Dev One"})
        assert form.is_valid(), form.errors

    def test_preferred_language_optional(self):
        """preferred_language can be omitted."""
        form = UserProfileForm(data={"display_name": "Alice"})
        assert form.is_valid(), form.errors

    def test_preferred_language_provided(self):
        form = UserProfileForm(data={
            "display_name": "Alice",
            "preferred_language": "Python",
        })
        assert form.is_valid(), form.errors


@pytest.mark.unit
class TestUserProfileFormAdminRejection:
    """Display names containing 'admin' (case-insensitive) must be rejected."""

    def test_admin_lowercase_rejected(self):
        form = UserProfileForm(data={"display_name": "admin"})
        assert not form.is_valid()
        assert "display_name" in form.errors

    def test_admin_uppercase_rejected(self):
        form = UserProfileForm(data={"display_name": "ADMIN"})
        assert not form.is_valid()
        assert "display_name" in form.errors

    def test_admin_mixed_case_rejected(self):
        form = UserProfileForm(data={"display_name": "Admin"})
        assert not form.is_valid()
        assert "display_name" in form.errors

    def test_admin_as_substring_rejected(self):
        form = UserProfileForm(data={"display_name": "superadmin"})
        assert not form.is_valid()
        assert "display_name" in form.errors

    def test_admin_prefix_rejected(self):
        form = UserProfileForm(data={"display_name": "adminUser"})
        assert not form.is_valid()
        assert "display_name" in form.errors

    def test_admin_suffix_rejected(self):
        form = UserProfileForm(data={"display_name": "useradmin"})
        assert not form.is_valid()
        assert "display_name" in form.errors

    def test_error_message_mentions_admin(self):
        form = UserProfileForm(data={"display_name": "admin"})
        form.is_valid()
        errors = " ".join(form.errors.get("display_name", []))
        assert "admin" in errors.lower()


@pytest.mark.unit
class TestUserProfileFormLengthValidation:
    """Display names under 3 characters must be rejected."""

    def test_empty_name_rejected(self):
        form = UserProfileForm(data={"display_name": ""})
        assert not form.is_valid()
        assert "display_name" in form.errors

    def test_one_char_name_rejected(self):
        form = UserProfileForm(data={"display_name": "A"})
        assert not form.is_valid()
        assert "display_name" in form.errors

    def test_two_char_name_rejected(self):
        """Boundary: exactly 2 characters (< 3) is rejected."""
        form = UserProfileForm(data={"display_name": "AB"})
        assert not form.is_valid()
        assert "display_name" in form.errors

    def test_error_message_mentions_characters(self):
        form = UserProfileForm(data={"display_name": "AB"})
        form.is_valid()
        errors = " ".join(form.errors.get("display_name", []))
        assert "3" in errors or "character" in errors.lower()


@pytest.mark.unit
@pytest.mark.django_db
class TestUserProfileFormSave:
    """Form.save() persists data to the UserProfile model."""

    def test_form_save_creates_profile(self, user):
        profile = UserProfile(user=user)
        form = UserProfileForm(
            data={"display_name": "SavedDev", "preferred_language": "Python"},
            instance=profile,
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        assert saved.display_name == "SavedDev"
        assert saved.preferred_language == "Python"

    def test_form_save_updates_existing_profile(self, user):
        profile = UserProfile.objects.create(user=user, display_name="OldName")
        form = UserProfileForm(
            data={"display_name": "NewName"},
            instance=profile,
        )
        assert form.is_valid(), form.errors
        updated = form.save()
        assert updated.display_name == "NewName"

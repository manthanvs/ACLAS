from django import forms
from .models import UserProfile
from django.core.exceptions import ValidationError

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['display_name', 'preferred_language']

    def clean_display_name(self):
        display_name = self.cleaned_data.get('display_name')
        if 'admin' in display_name.lower():
            raise ValidationError("You cannot use 'admin' in your display name.")
        if len(display_name) < 3:
            raise ValidationError("Display name must be at least 3 characters.")
        return display_name

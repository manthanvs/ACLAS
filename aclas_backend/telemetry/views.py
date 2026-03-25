from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from .models import UserProfile
from .forms import UserProfileForm

@login_required
def settings_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('settings')
    else:
        form = UserProfileForm(instance=profile)

    from rest_framework.authtoken.models import Token
    api_token, _ = Token.objects.get_or_create(user=request.user)
    return render(request, 'telemetry/settings.html', {
        'form': form,
        'api_token': api_token.key,
    })



def is_manager(user):
    return user.groups.filter(name='Manager').exists()

@user_passes_test(is_manager)
def manager_dashboard(request):
    return HttpResponse("<h1>ACLAS Manager Dashboard</h1><p>Only users in the Manager group can see telemetry data for the whole team.</p>")

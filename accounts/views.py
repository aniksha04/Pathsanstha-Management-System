from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from accounts.forms import StaffLoginForm, StaffCreateForm, StaffEditForm
from accounts.models import StaffProfile
from accounts.permissions import admin_required


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = StaffLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = StaffLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('login')


@login_required
@admin_required
def staff_list(request):
    staff_members = StaffProfile.objects.select_related('user', 'branch').order_by('-created_at')
    superusers_without_profile = User.objects.filter(is_superuser=True, staffprofile__isnull=True)
    return render(request, 'accounts/staff_list.html', {
        'staff_members': staff_members,
        'superusers': superusers_without_profile,
    })


@login_required
@admin_required
def staff_create(request):
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Staff account for {user.username} created successfully!")
            return redirect('staff_list')
    else:
        form = StaffCreateForm()

    return render(request, 'accounts/staff_form.html', {
        'form': form,
        'title': 'Create New Staff Member',
        'is_edit': False,
    })


@login_required
@admin_required
def staff_edit(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = StaffEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Staff account for {user_obj.username} updated successfully!")
            return redirect('staff_list')
    else:
        form = StaffEditForm(instance=user_obj)

    return render(request, 'accounts/staff_form.html', {
        'form': form,
        'target_user': user_obj,
        'title': f'Edit Staff Member: {user_obj.username}',
        'is_edit': True,
    })

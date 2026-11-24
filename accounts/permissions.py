from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from accounts.models import StaffProfile


def get_staff_profile(user):
    """Safely retrieves the StaffProfile for a given user."""
    if not user or not user.is_authenticated:
        return None
    try:
        return user.staffprofile
    except (StaffProfile.DoesNotExist, AttributeError):
        return None


def get_user_role(user):
    """
    Returns the effective role of the user.
    Superusers default to ADMIN if no profile exists.
    """
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'ADMIN'
    profile = get_staff_profile(user)
    if profile:
        return profile.role
    return None


def get_user_branch(user):
    """
    Returns the assigned Branch for the user.
    Admin returns None (unrestricted branch access) unless a branch is specifically assigned.
    """
    profile = get_staff_profile(user)
    if profile and profile.branch:
        return profile.branch
    return None


def is_admin(user):
    """Checks if the user has full administrative privileges."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = get_staff_profile(user)
    return profile is not None and profile.role == 'ADMIN'


def is_manager(user):
    """Checks if the user is a Manager (or Admin)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = get_staff_profile(user)
    return profile is not None and profile.role in ['ADMIN', 'MANAGER']


def is_accountant(user):
    """Checks if the user is an Accountant, Manager, or Admin."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = get_staff_profile(user)
    return profile is not None and profile.role in ['ADMIN', 'MANAGER', 'ACCOUNTANT']


def can_manage_members(user):
    """Only Admin and Manager can register or edit members. Accountants CANNOT."""
    return is_manager(user)


def can_manage_branches(user):
    """Only Admin can manage branches."""
    return is_admin(user)


def can_manage_staff(user):
    """Only Admin can manage staff/employees."""
    return is_admin(user)


def can_approve_loans(user):
    """Only Admin and Manager can approve or reject loans."""
    return is_manager(user)


def can_disburse_loans(user):
    """Only Admin and Manager can disburse loans."""
    return is_manager(user)


def can_perform_transactions(user):
    """Admin, Manager, and Accountant can perform deposits, withdrawals, and repayments."""
    return is_accountant(user)


def filter_by_branch(queryset, user, branch_field='branch'):
    """
    Applies branch-level data segregation to a queryset.
    Admins see records across all branches.
    Managers and Accountants strictly see only their assigned branch.
    """
    if is_admin(user):
        return queryset

    profile = get_staff_profile(user)
    if not profile or not profile.branch_id:
        return queryset.none()

    filter_kwargs = {branch_field: profile.branch}
    return queryset.filter(**filter_kwargs)


def check_branch_access(user, obj, branch_attr='branch'):
    """
    Verifies that the user has permission to access the target object based on branch.
    Raises PermissionDenied if the user is unauthorized.
    """
    if is_admin(user):
        return True

    profile = get_staff_profile(user)
    if not profile or not profile.branch_id:
        raise PermissionDenied("You do not have an assigned branch.")

    # Get target branch
    target_branch = getattr(obj, branch_attr, None)
    # Support if target object is itself a Branch
    if hasattr(obj, 'branch_code') and hasattr(obj, 'branch_name'):
        target_branch = obj

    if target_branch is None or target_branch.id != profile.branch_id:
        raise PermissionDenied("You are not authorized to access records from another branch.")

    return True


# View Decorators
def role_required(allowed_roles):
    """Decorator to restrict view access to specific staff roles."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            user_role = get_user_role(request.user)
            if not user_role or user_role not in allowed_roles:
                raise PermissionDenied("You do not have permission to access this resource.")

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """Restricts access to ADMIN only."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not is_admin(request.user):
            raise PermissionDenied("Administrative privileges required.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def manager_required(view_func):
    """Restricts access to MANAGER or ADMIN."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not is_manager(request.user):
            raise PermissionDenied("Managerial privileges required.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def accountant_required(view_func):
    """Restricts access to ACCOUNTANT, MANAGER, or ADMIN."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not is_accountant(request.user):
            raise PermissionDenied("Staff access privileges required.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

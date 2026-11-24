from accounts.permissions import (
    get_staff_profile,
    get_user_role,
    get_user_branch,
    is_admin,
    is_manager,
    is_accountant,
    can_manage_members,
    can_manage_branches,
    can_manage_staff,
    can_approve_loans,
    can_disburse_loans,
)


def auth_staff_context(request):
    """
    Supplies consistent staff role, branch, and capability flags to all templates.
    """
    if not request.user.is_authenticated:
        return {
            'user_role': None,
            'user_branch': None,
            'is_admin': False,
            'is_manager': False,
            'is_accountant': False,
            'can_manage_members': False,
            'can_manage_branches': False,
            'can_manage_staff': False,
            'can_approve_loans': False,
            'can_disburse_loans': False,
        }

    role = get_user_role(request.user)
    branch = get_user_branch(request.user)

    return {
        'user_role': role,
        'user_branch': branch,
        'is_admin': is_admin(request.user),
        'is_manager': is_manager(request.user),
        'is_accountant': is_accountant(request.user),
        'can_manage_members': can_manage_members(request.user),
        'can_manage_branches': can_manage_branches(request.user),
        'can_manage_staff': can_manage_staff(request.user),
        'can_approve_loans': can_approve_loans(request.user),
        'can_disburse_loans': can_disburse_loans(request.user),
    }

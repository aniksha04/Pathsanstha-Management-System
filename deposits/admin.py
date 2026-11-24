
from django.contrib import admin
from .models import AccountType, Account
from loans.permissions import is_manager, is_accountant


@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'interest_rate',
        'minimum_balance',
        'is_active'
    )

    def has_module_permission(self, request):
        return is_manager(request.user)

    def has_view_permission(self, request, obj=None):
        return is_manager(request.user)

    def has_add_permission(self, request):
        return is_manager(request.user)

    def has_change_permission(self, request, obj=None):
        return is_manager(request.user)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):

    list_display = (
        'account_number',
        'member',
        'account_type',
        'branch',
        'current_balance',
        'status',
    )

    list_filter = (
        'account_type',
        'branch',
        'status'
    )

    search_fields = (
        'account_number',
        'member__full_name'
    )

    def get_staff_profile(self, request):
        try:
            return request.user.staffprofile
        except Exception:
            return None

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        profile = self.get_staff_profile(request)

        if not profile:
            return qs.none()

        if profile.role == 'ADMIN':
            return qs

        if profile.branch:
            return qs.filter(branch=profile.branch)

        return qs.none()

    def has_module_permission(self, request):
        return is_accountant(request.user)

    def has_view_permission(self, request, obj=None):
        if not is_accountant(request.user):
            return False

        if obj is None:
            return True

        if request.user.is_superuser:
            return True

        profile = self.get_staff_profile(request)

        if not profile:
            return False

        if profile.role == 'ADMIN':
            return True

        return profile.branch_id == obj.branch_id

    def has_add_permission(self, request):
        return is_manager(request.user)

    def has_change_permission(self, request, obj=None):
        if not is_manager(request.user):
            return False

        if obj is None:
            return True

        if request.user.is_superuser:
            return True

        profile = self.get_staff_profile(request)

        if not profile:
            return False

        if profile.role == 'ADMIN':
            return True

        return profile.branch_id == obj.branch_id

    def has_delete_permission(self, request, obj=None):
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        profile = self.get_staff_profile(request)

        if (
            profile
            and profile.role == 'MANAGER'
            and profile.branch
        ):

            if db_field.name == 'member':
                kwargs['queryset'] = (
                    db_field.remote_field.model.objects.filter(
                        branch=profile.branch
                    )
                )

            elif db_field.name == 'branch':
                kwargs['queryset'] = (
                    db_field.remote_field.model.objects.filter(
                        id=profile.branch_id
                    )
                )

        return super().formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def get_readonly_fields(self, request, obj=None):

        if obj is None:
            return (
                'current_balance',
                'opened_at',
            )

        return (
            'account_number',
            'member',
            'account_type',
            'branch',
            'opening_balance',
            'current_balance',
            'opened_at',
        )

    def save_model(self, request, obj, form, change):

        if not change:
            profile = self.get_staff_profile(request)

            if not request.user.is_superuser and profile:
                if profile.role == 'MANAGER':
                    obj.branch = profile.branch

                    if (
                        not obj.branch
                        or obj.member.branch_id != obj.branch_id
                    ):
                        raise ValueError(
                            "You can only create accounts for members "
                            "of your assigned branch."
                        )

            obj.current_balance = obj.opening_balance

        super().save_model(request, obj, form, change)

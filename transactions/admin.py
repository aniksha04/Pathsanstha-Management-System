
from django.contrib import admin

from .models import Transaction
from loans.permissions import is_accountant


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):

    list_display = (
        'transaction_number',
        'account',
        'transaction_type',
        'amount',
        'status',
        'created_by',
        'created_at',
    )

    list_filter = (
        'transaction_type',
        'status',
        'created_at',
    )

    search_fields = (
        'transaction_number',
        'account__account_number',
    )

    readonly_fields = (
        'transaction_number',
        'account',
        'loan_payment',
        'transaction_type',
        'amount',
        'description',
        'created_by',
        'status',
        'created_at',
    )

    def get_staff_profile(self, request):
        try:
            return request.user.staffprofile
        except Exception:
            return None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if request.user.is_superuser:
            return queryset

        profile = self.get_staff_profile(request)

        if not profile:
            return queryset.none()

        if profile.role == 'ADMIN':
            return queryset

        if profile.branch_id:
            return queryset.filter(
                account__branch_id=profile.branch_id
            )

        return queryset.none()

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

        return (
            obj.account_id is not None
            and obj.account.branch_id == profile.branch_id
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

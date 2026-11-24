
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import LoanProduct, Loan, LoanRepayment, LoanPayment
from .permissions import is_admin, is_manager, is_accountant


class BranchAccessMixin:

    def get_staff_profile(self, request):
        try:
            return request.user.staffprofile
        except Exception:
            return None

    def is_global_admin(self, request):
        return request.user.is_superuser or is_admin(request.user)

    def get_branch_id(self, request):
        profile = self.get_staff_profile(request)
        return profile.branch_id if profile else None


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):

    list_display = (
        'loan_name',
        'interest_rate',
        'min_amount',
        'max_amount',
        'interest_method',
        'is_active',
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
        return is_manager(request.user)


@admin.register(Loan)
class LoanAdmin(BranchAccessMixin, admin.ModelAdmin):

    list_display = (
        'loan_number',
        'member',
        'loan_product',
        'principal_amount',
        'outstanding_balance',
        'status',
    )

    list_filter = ('status', 'loan_product')

    search_fields = (
        'loan_number',
        'member__full_name',
    )

    def get_queryset(self, request):

        queryset = super().get_queryset(request)

        if self.is_global_admin(request):
            return queryset

        if is_manager(request.user):
            branch_id = self.get_branch_id(request)

            if branch_id:
                return queryset.filter(branch_id=branch_id)

        return queryset.none()

    def has_module_permission(self, request):
        return is_manager(request.user)

    def has_view_permission(self, request, obj=None):

        if not is_manager(request.user):
            return False

        if self.is_global_admin(request):
            return True

        branch_id = self.get_branch_id(request)

        if obj is None:
            return bool(branch_id)

        return bool(branch_id and obj.branch_id == branch_id)

    def has_add_permission(self, request):
        return is_manager(request.user)

    def has_change_permission(self, request, obj=None):

        if not is_manager(request.user):
            return False

        if self.is_global_admin(request):
            return True

        branch_id = self.get_branch_id(request)

        if obj is None:
            return bool(branch_id)

        return bool(branch_id and obj.branch_id == branch_id)

    # Loans should not be permanently deleted
    def has_delete_permission(self, request, obj=None):
        return False

    # Restrict member and branch choices
    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if not self.is_global_admin(request):

            branch_id = self.get_branch_id(request)

            if db_field.name == 'member':
                if is_manager(request.user) and branch_id:
                    kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                        branch_id=branch_id
                    )
                else:
                    kwargs['queryset'] = db_field.remote_field.model.objects.none()

            elif db_field.name == 'branch':
                if is_manager(request.user) and branch_id:
                    kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                        pk=branch_id
                    )
                else:
                    kwargs['queryset'] = db_field.remote_field.model.objects.none()

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )

    # Validate branch and member before saving
    def save_model(self, request, obj, form, change):

        if not self.is_global_admin(request):

            branch_id = self.get_branch_id(request)

            if not is_manager(request.user) or not branch_id:
                raise PermissionError(
                    "You are not authorized to manage loans."
                )

            obj.branch_id = branch_id

        if obj.member_id and obj.branch_id:
            if obj.member.branch_id != obj.branch_id:
                raise ValidationError(
                    "Loan branch must match the member's branch."
                )

        super().save_model(request, obj, form, change)


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(BranchAccessMixin, admin.ModelAdmin):

    list_display = (
        'loan',
        'installment_number',
        'due_date',
        'total_due',
        'amount_paid',
        'status',
    )

    list_filter = ('status', 'due_date')

    def get_queryset(self, request):

        queryset = super().get_queryset(request)

        if self.is_global_admin(request):
            return queryset

        branch_id = self.get_branch_id(request)

        if is_accountant(request.user) and branch_id:
            return queryset.filter(loan__branch_id=branch_id)

        return queryset.none()

    def has_module_permission(self, request):
        return is_accountant(request.user)

    def has_view_permission(self, request, obj=None):

        if not is_accountant(request.user):
            return False

        if self.is_global_admin(request):
            return True

        branch_id = self.get_branch_id(request)

        if obj is None:
            return bool(branch_id)

        return bool(
            branch_id and obj.loan.branch_id == branch_id
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LoanPayment)
class LoanPaymentAdmin(BranchAccessMixin, admin.ModelAdmin):

    list_display = (
        'receipt_number',
        'loan',
        'amount',
        'payment_mode',
        'payment_date',
        'received_by',
    )

    search_fields = (
        'receipt_number',
        'loan__loan_number',
    )

    list_filter = (
        'payment_mode',
        'payment_date',
    )

    readonly_fields = (
        'loan',
        'repayment',
        'receipt_number',
        'amount',
        'payment_date',
        'payment_mode',
        'received_by',
    )

    def get_queryset(self, request):

        queryset = super().get_queryset(request)

        if self.is_global_admin(request):
            return queryset

        branch_id = self.get_branch_id(request)

        if is_accountant(request.user) and branch_id:
            return queryset.filter(loan__branch_id=branch_id)

        return queryset.none()

    def has_module_permission(self, request):
        return is_accountant(request.user)

    def has_view_permission(self, request, obj=None):

        if not is_accountant(request.user):
            return False

        if self.is_global_admin(request):
            return True

        branch_id = self.get_branch_id(request)

        if obj is None:
            return bool(branch_id)

        return bool(
            branch_id and obj.loan.branch_id == branch_id
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

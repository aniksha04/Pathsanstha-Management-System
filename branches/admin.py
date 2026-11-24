
from django.contrib import admin

from .models import Branch
from loans.permissions import is_admin, is_manager


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):

    list_display = (
        'branch_name',
        'branch_code',
        'phone',
        'is_active',
        'created_at'
    )

    search_fields = (
        'branch_name',
        'branch_code',
        'address'
    )

    list_filter = ('is_active',)

    def get_staff_profile(self, request):
        try:
            return request.user.staffprofile
        except Exception:
            return None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if request.user.is_superuser or is_admin(request.user):
            return queryset

        profile = self.get_staff_profile(request)

        if profile and profile.role == 'MANAGER' and profile.branch_id:
            return queryset.filter(id=profile.branch_id)

        return queryset.none()

    def has_module_permission(self, request):
        return is_manager(request.user)

    def has_view_permission(self, request, obj=None):

        if not is_manager(request.user):
            return False

        if request.user.is_superuser or is_admin(request.user):
            return True

        profile = self.get_staff_profile(request)

        if not profile or profile.role != 'MANAGER':
            return False

        if obj is None:
            return bool(profile.branch_id)

        return obj.id == profile.branch_id

    def has_add_permission(self, request):
        return is_admin(request.user)

    def has_change_permission(self, request, obj=None):

        if not is_admin(request.user):
            return False

        return True

    def has_delete_permission(self, request, obj=None):
        return is_admin(request.user)

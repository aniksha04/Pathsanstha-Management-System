
from django.contrib import admin

from .models import Member
from loans.permissions import is_admin, is_manager


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):

    list_display = (
        'member_number',
        'full_name',
        'phone',
        'branch',
        'status',
    )

    list_filter = (
        'status',
        'gender',
        'branch',
    )

    search_fields = (
        'member_number',
        'full_name',
        'phone',
    )

    ordering = ('member_number',)

    # Member number is now editable
    readonly_fields = (
        'joined_date',
        'created_at',
        'updated_at',
    )

    def get_staff_profile(self, request):
        try:
            return request.user.staffprofile
        except Exception:
            return None

    # Control access to Member section
    def has_module_permission(self, request):
        return is_manager(request.user)

    # Restrict records according to staff branch
    def get_queryset(self, request):

        queryset = super().get_queryset(request)

        if request.user.is_superuser or is_admin(request.user):
            return queryset

        profile = self.get_staff_profile(request)

        if profile and profile.role == 'MANAGER' and profile.branch_id:
            return queryset.filter(branch_id=profile.branch_id)

        return queryset.none()

    # Check permission to view individual member
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

        return obj.branch_id == profile.branch_id

    # Control member registration
    def has_add_permission(self, request):
        return is_manager(request.user)

    # Check permission to edit individual member
    def has_change_permission(self, request, obj=None):

        if not is_manager(request.user):
            return False

        if request.user.is_superuser or is_admin(request.user):
            return True

        profile = self.get_staff_profile(request)

        if not profile or profile.role != 'MANAGER':
            return False

        if obj is None:
            return bool(profile.branch_id)

        return obj.branch_id == profile.branch_id

    # Restrict branch selection during registration
    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == 'branch':

            if not request.user.is_superuser and not is_admin(request.user):

                profile = self.get_staff_profile(request)

                if profile and profile.role == 'MANAGER' and profile.branch_id:
                    kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                        pk=profile.branch_id
                    )
                else:
                    kwargs['queryset'] = db_field.remote_field.model.objects.none()

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )

    # Prevent deletion of member records
    def has_delete_permission(self, request, obj=None):
        return False

    # Ensure a manager cannot submit another branch's ID manually
    def save_model(self, request, obj, form, change):

        if not request.user.is_superuser and not is_admin(request.user):

            profile = self.get_staff_profile(request)

            if not profile or profile.role != 'MANAGER' or not profile.branch_id:
                raise PermissionError("You are not authorized to register members.")

            obj.branch_id = profile.branch_id

        super().save_model(request, obj, form, change)


from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from .models import StaffProfile
from loans.permissions import is_admin


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'role',
        'branch',
        'created_at',
    )

    list_filter = (
        'role',
        'branch',
        'created_at',
    )

    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
    )

    ordering = ('role', 'user__username')

    readonly_fields = ('created_at',)

    list_per_page = 20

    def has_module_permission(self, request):
        return is_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_add_permission(self, request):
        return is_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_admin(request.user)


class RestrictedUserAdmin(UserAdmin):

    def has_module_permission(self, request):
        return is_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_add_permission(self, request):
        return is_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_admin(request.user)


admin.site.unregister(User)
admin.site.register(User, RestrictedUserAdmin)

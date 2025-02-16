from django.contrib import admin

from .models import CustomUser, Role, Permission, Follow



@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'get_role', 'verified', 'is_premium']
    list_filter = ['joined_at', 'is_premium', 'verified']
    show_facets = admin.ShowFacets.ALLOW
    list_per_page = 50

    @admin.display(description='Role')
    def get_role(self, obj):
        return obj.role.name if obj.role else 'No Role'


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_permissions']

    @admin.display(description='Permissions')
    def get_permissions(self, obj):
        permissions = obj.get_permissions() 
        return ", ".join(
            [Permission.get_name(perm) for perm in permissions]
        ) if permissions else "No Permissions"


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'followed', 'created_at']
    search_fields = ['follower', 'followed']
    list_filter = ['created_at']
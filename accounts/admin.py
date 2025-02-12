from django.contrib import admin

from .models import CustomUser, Role, Permission



@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'get_role', 'verified', 'is_premium']
    list_filter = ['joined_at', 'is_admin', 'is_premium', 'verified']
    show_facets = admin.ShowFacets.ALLOW
    list_per_page = 50

    @admin.display(description='Role')
    def get_role(self, obj):
        return str(obj.role).split()[0]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_permissions']

    @admin.display(description='Permissions')
    def get_permissions(self, obj):
        roles = {
            'User': [Permission.LIKE, Permission.COMMENT],
            'PremiumUser': [Permission.FOLLOW, Permission.LIKE, Permission.BOOKMARK,
                            Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.MODERATE_COMMENTS, Permission.COMMENT,
                         Permission.EDIT_ARTICLE, Permission.DELETE_ARTICLE],
            'Administrator': [Permission.ADMIN, Permission.FOLLOW, Permission.LIKE, 
                              Permission.BOOKMARK, Permission.COMMENT],
        }
        permissions = []
        for perm in roles[obj.name]:
            permissions.append(Permission.get_name(perm))
        
        return "-".join(permissions)
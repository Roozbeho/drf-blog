from rest_framework import permissions
from accounts.models import Permission

class CanUserWritePost(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return user.is_authenticated and user.can(Permission.WRITE)
    
class OwnerAndAdminOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        return obj.author == user or user.can(Permission.ADMIN)
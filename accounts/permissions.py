from rest_framework import permissions

class NotAuthenticatedUserOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return False
        return True
    

class NotVerifiedAccountOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return not request.user.verified
    
class VerifiedAccountOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.verified
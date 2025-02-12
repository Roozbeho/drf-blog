from django.contrib import admin

from .models import CustomUser



@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'is_admin', 'verified', 'is_premium']
    list_filter = ['joined_at', 'is_admin', 'is_premium', 'verified']
    show_facets = admin.ShowFacets.ALLOW
    list_per_page = 50


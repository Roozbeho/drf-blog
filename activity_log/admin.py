from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html, urlencode

from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogModelAdmin(admin.ModelAdmin):
    list_display = [
        "get_user",
        "action_type",
        "content_type",
        "get_content_object_link",
        "status",
        "action_time",
    ]
    list_filter = ["action_type", "status", "action_time"]
    search_fields = ["user"]
    show_facets = admin.ShowFacets.ALLOW
    list_per_page = 50
    list_select_related = ["user", "content_type"]

    @admin.display(description="Model Instance")
    def get_content_object_link(self, obj):
        try:
            obj_content_type = ContentType.objects.get_for_model(obj.content_object)
            url = reverse(
                f"admin:{obj_content_type.app_label}_{obj_content_type.model}_change",
                args=[obj.object_id],
            )
            return format_html(
                f'<a href="{url}">{obj.content_object.__str__()[:20]} ...</a>'
            )
        except AttributeError:
            return obj.content_object

    @admin.display(description="User")
    def get_user(self, obj):
        return obj.user.username if obj.user else "Unknown user"

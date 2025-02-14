from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, urlencode

from .models import Post, PostImage, Tag, Like


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "link_to_posts_page"]
    search_fields = ["name", 'slug']
    list_per_page = 50
    show_facets = admin.ShowFacets.ALLOW
    prepopulated_fields = {
        "slug": [
            "name",
        ]
    }

    @admin.display(description="Number of posts")
    def link_to_posts_page(self, obj):
        link = reverse("admin:blog_post_changelist") + "?" + urlencode({"category__id": obj.id})
        return format_html(f'<a href="{link}">{obj.number_of_posts} posts</a>')


class PostImageInline(admin.TabularInline):
    model = PostImage


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        "show_title",
        "link_to_author",
        "status",
        "premium",
        "visit_counter",
        "show_published_time",
    ]
    list_filter = ["status", "premium", "published_at"]
    search_fields = ["title"]
    show_facets = admin.ShowFacets.ALLOW
    list_per_page = 50
    list_select_related = ["author"]
    inlines = [PostImageInline]

    def link_to_author(self, obj):
        link = reverse("admin:accounts_customuser_change", args=[obj.author.pk])
        return format_html(f'<a href="{link}">{str(obj.author).split('-')[0].split(':')[-1]}</a>')

    def show_title(self, obj):
        return obj.title[:10]

    @admin.display(description="Published time")
    def show_published_time(self, obj):
        if obj.status == obj.Status.PUBLISHED and obj.published_at:
            return obj.published_at.strftime("%Y/%m/%d - %H:%M")
        return ""

@admin.register(Like)
class Likeadmin(admin.ModelAdmin):
    list_display = ['get_user', 'get_post', 'created_at']
    search_fields = ['user', 'post']
    list_filter = ['created_at']
    list_per_page = 100
    list_select_related = ['user', 'post']


    @admin.display(description='User')
    def get_user(self, obj):
        link = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html(f'<a href="{link}">{obj.user.username}</a>')
    
    @admin.display(description='Post')
    def get_post(self, obj):
        link = reverse('admin:blog_post_change', args=[obj.post.pk])
        return format_html(f'<a href="{link}">{obj.post.title[:20]}</a>')
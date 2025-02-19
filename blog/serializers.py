from django.conf import settings
from django.db import transaction
from django.urls import reverse
from rest_framework import serializers

from .models import Comment, Post, PostImage, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("name",)


class PostsListSerializer(serializers.ModelSerializer):
    # TODO: url, url for tag fitler, url for author,
    url = serializers.HyperlinkedIdentityField(view_name="blog:post-detail", lookup_field="slug")
    content_overview = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    tag = TagSerializer(many=True)

    class Meta:
        model = Post
        fields = (
            "url",
            "author",
            "slug",
            "title",
            "content_overview",
            "thumbnail_url",
            "visit_counter",
            "published_at",
            "tag",
        )

    def get_content_overview(self, obj):
        return obj.content_overview

    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            return obj.thumbnail.url
        return settings.DEFAULT_THUMBNAIL_URL


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ["image", "alt"]

    def validate_image(self, value):
        if value.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            raise serializers.ValidationError("Image size to big")
        return value


class PostDetailSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    images = PostImageSerializer(read_only=True, many=True)
    tag = TagSerializer(many=True)

    # TODO: linkn to user, link to tags
    class Meta:
        model = Post
        fields = (
            "author",
            "title",
            "body",
            "body_html",
            "published_at",
            "visit_counter",
            "thumbnail_url",
            "images",
            "tag",
        )

        read_only_fields = ["author", "body_html", "published_at", "visit_counter", "images"]

    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            return obj.thumbnail.url
        return settings.DEFAULT_THUMBNAIL_URL

    @transaction.atomic
    def create(self, validated_data):
        author = self.context.get("request").user
        tags = validated_data.pop("tag", [])

        instance = Post.objects.create(author=author, **validated_data)
        instance.tag.add(*tags)

        return instance


class CreateAndManagementPostSerializer(serializers.ModelSerializer):
    tag = serializers.SlugRelatedField(queryset=Tag.objects.all(), slug_field="slug", many=True)

    class Meta:
        model = Post
        fields = ("author", "title", "body", "thumbnail", "published_at", "tag", "status")

        read_only_fields = ["author", "stauts", "visit_counter"]

    @transaction.atomic
    def create(self, validated_data):
        author = self.context.get("request").user
        tags = validated_data.pop("tag", [])

        instance = Post.objects.create(author=author, **validated_data)
        instance.tag.add(*tags)

        return instance

    @transaction.atomic
    def update(self, instance: Post, validated_data):
        body = validated_data.get("body", instance.body)
        if body != instance.body:
            instance.body = body
            instance.body_html = instance.on_changed_body()

        instance.title = validated_data.get("title", instance.title)
        instance.thumbnail = validated_data.get("thumbnail", instance.thumbnail)

        tags = validated_data.get("tag", instance.tag.all())
        exist_tags = set(instance.tag.all())
        tags_to_add = [tag for tag in tags if tag not in exist_tags]

        if tags_to_add:
            instance.add(**tags_to_add)

        instance.save()
        return instance


class PostImageSerializer(serializers.ModelSerializer):
    post = serializers.SlugRelatedField(queryset=Post.objects.all(), slug_field="slug")

    class Meta:
        model = PostImage
        fields = ["pk", "post", "image", "alt"]
        read_only_fields = ["pk"]

    def validate_post(self, value):
        if not Post.objects.filter(slug=value).exists():
            serializers.ValidationError("post dosent exist")
        return value


class TagListSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="blog:post-by-tag", lookup_field="slug")

    class Meta:
        model = Tag
        fields = ["url", "name"]


class CommentSerializer(serializers.ModelSerializer):
    post = serializers.HyperlinkedRelatedField(read_only="True", view_name="blog:post-detail", lookup_field="slug")

    class Meta:
        model = Comment
        fields = ["user", "post", "content", "created_at"]

    def get_fields(self):
        fields = super(CommentSerializer, self).get_fields()
        fields["reply"] = CommentSerializer(many=True)
        if self.context.get("is_owner"):
            fields["reply_link"] = serializers.SerializerMethodField()
        return fields

    def get_reply_link(self, obj):
        return f"{reverse('blog:post-commnts-reply', args=[obj.post.slug, obj.uuid])}"


class CreateCommentSerializer(serializers.ModelSerializer):
    parent_comment = serializers.PrimaryKeyRelatedField(
        required=False, queryset=Comment.objects.filter(is_active=True), pk_field="uuid"
    )

    class Meta:
        model = Comment
        fields = ["content", "parent_comment"]

    def create(self, validated_data):
        user = self.context.get("request").user
        post = self.context.get("post")
        parent_comment = self.context.get("parent_comment", None)

        return Comment.objects.create(user=user, post=post, parent_comment=parent_comment, **validated_data)


class UsersUpdateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["content"]


class AdminUpdateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["content", "is_active"]

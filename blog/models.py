import string
import bleach
from random import choices
from markdown import markdown

from django.db import models
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator

from .managers import PostCustomManager

class Tag(models.Model):
    slug = models.SlugField(max_length=30, unique=True, db_index=True)
    name = models.CharField(max_length=30)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(Tag, self).save(*args, **kwargs)

    @property
    def number_of_posts(self):
        return self.posts.count()

    def __str__(self):
        return self.name

def thumbnail_path(instance, filename):
    return f"posts/{instance.title}/post_thumbnail/{filename}"

class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DR", "Draft"
        PUBLISHED = "PUB", "Published"
        ARCHIVED = "AR", "Archived"

    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    body = models.TextField()
    body_html = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to=thumbnail_path, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    visit_counter = models.IntegerField(editable=False, default=0)
    premium = models.BooleanField(default=False, help_text='thise post only available for premium users')
    author = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='posts')
    tag = models.ManyToManyField(Tag, related_name='posts')
    is_active = models.BooleanField(default=True)
    published_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    active_objects = PostCustomManager()

    class Meta:
        ordering = ('-published_at', )
        indexes = [
            models.Index(fields=('-published_at', )),
            models.Index(fields=('slug', ))
        ]

    def on_changed_body(self):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'ore',
                        'strong', 'ul', 'h1', 'h2',' h3', 'p']
        return bleach.linkify(bleach.clean(
            markdown(self.body, output_format='html'),
            tags=allowed_tags, strip=True))

    @property
    def content_overview(self):
        return self.body[: 50]

    @classmethod
    def create_custom_slug(cls, title):
        characters = string.ascii_letters + string.digits
        slug = slugify(title) + '-' + ''.join(choices(characters, k=10))

        while cls.objects.filter(slug=slug).exists():
            slug = slugify(title) + '-' + ''.join(choices(characters, k=10))
        return slug
    
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = Post.create_custom_slug(self.title)
        if not self.body_html:
            self.body_html = self.on_changed_body()

        super(Post, self).save(*args, **kwargs)
        
    def __str__(self):
        return f'{self.title} - {self.author.username} - {self.status}'
    
def post_image_path_to(instance, filename):
    return f"posts/{instance.post.title}/post_image/{filename}"

class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to=post_image_path_to,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    alt = models.CharField(max_length=50, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Image {self.id} for {self.post.title}'
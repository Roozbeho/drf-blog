# Generated by Django 5.1.6 on 2025-02-13 14:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0004_alter_post_body_html"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]

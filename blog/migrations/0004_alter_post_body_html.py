# Generated by Django 5.1.6 on 2025-02-13 13:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0003_alter_post_slug"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="body_html",
            field=models.TextField(blank=True),
        ),
    ]

# Generated by Django 5.1.6 on 2025-02-13 08:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="slug",
            field=models.CharField(blank=True, max_length=100, unique=True),
        ),
    ]

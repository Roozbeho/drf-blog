# Generated by Django 5.1.6 on 2025-02-14 11:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0006_like"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="like",
            options={"ordering": ("-created_at",)},
        ),
    ]

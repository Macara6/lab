# Generated by Django 5.1.4 on 2025-05-11 22:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Myapp", "0008_userprofile_adress_userprofile_entrep_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="subscription_type",
            field=models.CharField(
                choices=[
                    ("BASIC", "Basic"),
                    ("MEDIUM", "Medium"),
                    ("PREMIUM", "Premium"),
                ],
                default="BASIC",
                max_length=10,
            ),
        ),
    ]


from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime
from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def generate_custom_account_id(sender, instance, created,**kwargs):
    if created and not instance.custom_account_id:
        user_id = instance.id
        month = instance.date_joined.month
        year = instance.date_joined.year

        custom_id = f"BL-S{user_id:03d}-{month:02d}{year}"
        instance.custom_account_id = custom_id
        instance.save(update_fields=['custom_account_id'])




from django.core.management.base import BaseCommand
from django.utils.timezone import now, timedelta
from django.contrib.auth import get_user_model
User = get_user_model()


class Command(BaseCommand):
    help = "Supprime automatiquement les utilisateurs dans la corbeille depuis plus de 30 jours"

    def handle(self, *args, **kwargs):
        cutoff_date = now() - timedelta(days=30)
        users_to_delete = User.objects.filter(is_deleted=True, deleted_at__lt=cutoff_date)
        count = users_to_delete.count()
        users_to_delete.delete()
        self.stdout.write(f"{count} utilisateurs définitivement supprimés.")
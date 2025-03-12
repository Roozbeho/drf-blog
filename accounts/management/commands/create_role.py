from django.core.management.base import BaseCommand
from accounts.models import Role, Permission


class Command(BaseCommand):
    help = "Create Defaults Roles"

    def handle(self, *args, **options):
        Role.insert_roles()
        
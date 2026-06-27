import os

from django.core.management.base import BaseCommand
from billing.models import User


class Command(BaseCommand):
    help = 'Create default admin and accountant users if they do not exist'

    def handle(self, *args, **options):
        admin_username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        admin_email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@wistora.local')
        admin_password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')

        if not User.objects.filter(username=admin_username).exists():
            admin_user = User.objects.create_user(username=admin_username, email=admin_email, password=admin_password, role='admin')
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_username}'))

        accountant_username = os.getenv('DJANGO_ACCOUNTANT_USERNAME', 'accountant')
        accountant_email = os.getenv('DJANGO_ACCOUNTANT_EMAIL', 'accountant@wistora.local')
        accountant_password = os.getenv('DJANGO_ACCOUNTANT_PASSWORD', 'accountant123')

        if not User.objects.filter(username=accountant_username).exists():
            accountant_user = User.objects.create_user(username=accountant_username, email=accountant_email, password=accountant_password, role='accountant')
            accountant_user.is_staff = False
            accountant_user.is_superuser = False
            accountant_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created accountant user: {accountant_username}'))

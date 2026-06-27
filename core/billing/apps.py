import os

from django.apps import AppConfig, apps
from django.db.models.signals import post_migrate


def create_default_superuser(sender, **kwargs):
    User = apps.get_model('billing', 'User')
    if User.objects.exists():
        return

    username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@wistora.local')
    password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')

    user = User.objects.create(username=username, email=email, role='admin')
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'

    def ready(self):
        post_migrate.connect(create_default_superuser, sender=self)

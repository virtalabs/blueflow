from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from blueflow import permissions


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, *, instance=None, created=False, **__):  # noqa: ARG001
    if not created or instance is None:
        return

    Token.objects.create(user=instance)
    # by default all users get Viewer status on endpoints
    permissions.IsViewer.make_viewer(instance)

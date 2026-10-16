import typing

from django.contrib.auth import models
from rest_framework import permissions, request

class IsViewer(permissions.BasePermission):
    key = "Viewer"

    @classmethod
    def make_viewer(cls, user: models.User):
        g, _ = models.Group.objects.get_or_create(name=cls.key)
        user.groups.add(g)

    @typing.override
    def has_permission(self, request: request.Request, *_, **__) -> bool:
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        in_group = request.user.groups.filter(name=self.key).exists()
        return in_group and request.method in permissions.SAFE_METHODS

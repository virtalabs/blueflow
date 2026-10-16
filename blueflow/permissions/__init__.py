import typing

from django.contrib.auth import models
from rest_framework import permissions, request

User = models.User


class CanView:
    key = "blueflow.view_objects"

    def can_view(self, user: User) -> bool:
        return user.has_perm(self.key)


class CanCreate:
    key = "blueflow.create_objects"

    def can_create(self, user: User) -> bool:
        return user.has_perm(self.key)


class CanEdit:
    key = "blueflow.edit_objects"

    def can_edit(self, user: User) -> bool:
        return user.has_perm(self.key)


class CanDelete:
    key = "blueflow.delete_objects"

    def can_delete(self, user: User) -> bool:
        return user.has_perm(self.key)


class IsViewer(permissions.BasePermission, CanView):
    @classmethod
    def make_viewer(cls, user: User):
        perm, _ = models.Permission.objects.get_or_create(
            codename=CanView.key, name="Can View Objects"
        )
        user.user_permissions.add(perm)

    @typing.override
    def has_permission(self, request: request.Request, *_, **__) -> bool:
        if isinstance(request.user, models.PermissionsMixin):
            return request.user.has_perm(CanView.key)
        return False

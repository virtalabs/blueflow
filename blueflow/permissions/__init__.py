from django.contrib.auth import models
from rest_framework import permissions, request


class CanView:
    key = "view_objects"

    def can_view(self, user: models.User) -> bool:
        return user.has_perm(self.key)


class CanCreate:
    key = "create_objects"

    def can_delete(self, user: models.User) -> bool:
        return user.has_perm(self.key)


class CanEdit:
    key = "edit_objects"

    def can_edit(self, user: models.User) -> bool:
        return user.has_perm(self.key)


class CanDelete:
    key = "delete_objects"

    def can_delete(self, user: models.User) -> bool:
        return user.has_perm(self.key)


class IsViewer(permissions.BasePermission, CanView):
    @classmethod
    def make_viewer(cls, user: models.User):
        perm, _ = models.Permission.objects.get_or_create(
            codename=CanView.key, name="Can View Objects"
        )
        user.user_permissions.add(perm)

    def has_permissions(self, request: request.Request, **__) -> bool:
        return super().can_view(request.user)

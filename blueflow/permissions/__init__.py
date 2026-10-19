import typing
from collections import abc

from django.contrib.auth import models
from rest_framework import permissions, request


class IsPermission(permissions.BasePermission):
    key: str = ""
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods
    methods: abc.Sequence[str] = ("",)

    @classmethod
    def make(cls, user: models.User):
        if cls.key == "":
            msg = f"{cls} requires a non empty key."
            raise ValueError(msg)
        g, _ = models.Group.objects.get_or_create(name=cls.key)
        user.groups.add(g)

    @typing.override
    def has_permission(self, request: request.Request, *_, **__) -> bool:
        if self.methods == ("",):
            msg = f"{self.__class__} requires a non empty method sequence."
            raise ValueError(msg)

        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        in_group = request.user.groups.filter(name=self.key).exists()
        return in_group and request.method in self.methods


class IsViewer(IsPermission):
    """Defines the default view only permission."""

    key = "Viewer"
    methods = permissions.SAFE_METHODS

    @classmethod
    def make_viewer(cls, user: models.User):
        cls.make(user)


class IsBiomedical(IsPermission):
    """Defines the biomedical eng permission.

    Bio will _generally_ have access to most things. Save some admin
    specific duties. (user creation?).
    """

    key = "Biomedical"
    methods = (*permissions.SAFE_METHODS, "POST", "PUT", "DELETE")

    @classmethod
    def make_biomedical(cls, user: models.User):
        cls.make(user)


class IsAdmin(IsPermission):
    """Defines the admin permission.

    Admins should have unrestricted access.
    """

    key = "Admin"
    methods = (*permissions.SAFE_METHODS, "POST", "PUT", "DELETE")

    @classmethod
    def make_admin(cls, user: models.User):
        cls.make(user)

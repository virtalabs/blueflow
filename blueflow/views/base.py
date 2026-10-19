from rest_framework import permissions, views

from blueflow import permissions as bf_permissions


class IsGatedMixin(views.APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        bf_permissions.IsViewer | bf_permissions.IsBiomedical | bf_permissions.IsAdmin,
    )

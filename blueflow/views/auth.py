"""Endpoints for user authentication."""

from django import shortcuts
from django.contrib import auth
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import request, response, serializers, status, validators, views
from rest_framework.authtoken import models as rf_models

from blueflow import permissions


class Roles(models.TextChoices):
    admin = "admin", _("Administrator")
    bio = "bio", _("Biomedical")
    viewer = "viewer", _("Viewer")


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(allow_blank=False, min_length=5)
    password = serializers.CharField(allow_blank=False, min_length=5)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(
        allow_blank=False,
        min_length=5,
        validators=(
            validators.UniqueValidator(
                queryset=auth.get_user_model().objects.all(),
                message="Username not avilable",
            ),
        ),
    )
    password = serializers.CharField(allow_blank=False, min_length=5)
    role = serializers.ChoiceField(choices=Roles.choices, default=Roles.viewer)


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField(allow_blank=False, min_length=5)


class LoginView(views.APIView):
    def post(self, request: request.Request) -> response.Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = shortcuts.get_object_or_404(
            auth.get_user_model(), username=data["username"]
        )
        authed = auth.authenticate(username=data["username"], password=data["password"])
        if authed is None:
            return response.Response(status=status.HTTP_401_UNAUTHORIZED)
        token = rf_models.Token.objects.get(user=user)
        res = LoginResponseSerializer(data={"token": token.key})
        res.is_valid(raise_exception=True)
        return response.Response(res.validated_data, status=status.HTTP_200_OK)


class RegisterView(views.APIView):
    permission_classes = (permissions.IsAdmin,)

    def post(self, request: request.Request) -> response.Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = auth.get_user_model().objects.create(username=data["username"])
        user.set_password(data["password"])
        role = data["role"]
        if role == Roles.admin:
            permissions.IsAdmin.make_admin(user)
        elif role == Roles.bio:
            permissions.IsBiomedical.make_biomedical(user)
        user.save()
        user.refresh_from_db()
        token = rf_models.Token.objects.get(user=user)
        res = LoginResponseSerializer(data={"token": token.key})
        res.is_valid(raise_exception=True)
        return response.Response(res.validated_data, status=status.HTTP_200_OK)

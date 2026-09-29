from django.db import models


class ScopeChoices(models.TextChoices):
    boundary = "boundary"
    internal = "internal"

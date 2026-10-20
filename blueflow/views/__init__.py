"""API Views."""

from blueflow.serializers import AssetRequestSerializer

from .asset import AssetViewSet
from .assetgroup import AssetGroupSerializer, AssetGroupViewSet
from .assettag import AssetTagSerializer, AssetTagViewSet
from .auth import LoginView, RegisterView
from .group import GroupSerializer, GroupViewSet
from .network import Telemetry, Topology
from .periodic_task import (
    CrontabScheduleSerializer,
    CrontabScheduleViewSet,
    IntervalScheduleSerializer,
    IntervalScheduleViewSet,
    PeriodicTaskSerializer,
    PeriodicTaskViewSet,
)
from .tag import TagSerializer, TagViewSet
from .user import UserSerializer, UserViewSet
from .viper import ViperViewSet

__all__ = [
    "AssetGroupSerializer",
    "AssetGroupViewSet",
    "AssetRequestSerializer",
    "AssetTagSerializer",
    "AssetTagViewSet",
    "AssetViewSet",
    "CrontabScheduleSerializer",
    "CrontabScheduleViewSet",
    "GroupSerializer",
    "GroupViewSet",
    "IntervalScheduleSerializer",
    "IntervalScheduleViewSet",
    "LoginView",
    "PeriodicTaskSerializer",
    "PeriodicTaskViewSet",
    "RegisterView",
    "TagSerializer",
    "TagViewSet",
    "Telemetry",
    "Topology",
    "UserSerializer",
    "UserViewSet",
    "ViperViewSet",
]

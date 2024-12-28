# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import wraps
from typing import Callable, Collection

from cm.converters import core_type_to_model, host_group_type_to_model
from cm.models import Cluster, Component, Host, Service
from cm.services.status.client import retrieve_status_map
from cm.status_api import get_raw_status
from core.types import ADCMCoreType, ADCMHostGroupType, CoreObjectDescriptor, HostGroupDescriptor
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend
from djangorestframework_camel_case.parser import (
    CamelCaseFormParser,
    CamelCaseJSONParser,
    CamelCaseMultiPartParser,
)
from djangorestframework_camel_case.render import (
    CamelCaseBrowsableAPIRenderer,
    CamelCaseJSONRenderer,
)
from rest_framework.exceptions import NotFound
from rest_framework.mixins import (
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import AllowAny
from rest_framework.routers import APIRootView
from rest_framework.viewsets import GenericViewSet


class APIRoot(APIRootView):
    permission_classes = (AllowAny,)
    api_root_dict = {
        "adcm": "adcm-detail",
        "clusters": "cluster-list",
        "audit": "audit:root",
        "bundles": "bundle-list",
        "hosts": "host-list",
        "hostproviders": "provider-list",
        "prototypes": "prototype-list",
        "jobs": "joblog-list",
        "tasks": "tasklog-list",
        "rbac": "rbac:root",
    }


class CamelCaseBrowsableAPIRendererWithoutForms(CamelCaseBrowsableAPIRenderer):
    """Renders the browsable api, but excludes the forms."""

    def get_context(self, *args, **kwargs):
        ctx = super().get_context(*args, **kwargs)
        ctx["post_form"] = False
        ctx["put_form"] = False
        return ctx


class ADCMGenericViewSet(GenericViewSet):
    parser_classes = [CamelCaseJSONParser, CamelCaseMultiPartParser, CamelCaseFormParser]
    renderer_classes = [CamelCaseJSONRenderer, CamelCaseBrowsableAPIRendererWithoutForms]
    filter_backends = [DjangoFilterBackend]

    lookup_value_regex = r"\d+"


class ADCMReadOnlyModelViewSet(RetrieveModelMixin, ListModelMixin, ADCMGenericViewSet):
    pass


class ObjectWithStatusViewMixin:
    retrieve_status_map_actions: Collection[str] = ("list",)
    retrieve_single_status_actions: Collection[str] = ("retrieve", "update", "partial_update")

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()

        if self.action in self.retrieve_status_map_actions:
            return {**context, "status_map": retrieve_status_map()}

        if self.action == "create":
            return {**context, "status": 0}

        if self.action not in self.retrieve_single_status_actions:
            return context

        try:
            view_model = self.queryset.model
        except AttributeError as err:
            message = (
                f"{self.__class__} should have underlying model accessible via "
                "`self.queryset.model` to determine how to retrieve status for object"
            )
            raise AttributeError(message) from err

        url = None
        try:
            if view_model in (Cluster, Host):
                url = f"{view_model.__name__.lower()}/{self.kwargs['pk']}/"
            elif view_model == Service:
                url = f"cluster/{self.kwargs['cluster_pk']}/service/{self.kwargs['pk']}/"
            elif view_model == Component:
                url = (
                    f"cluster/{self.kwargs['cluster_pk']}/service/{self.kwargs['service_pk']}"
                    f"/component/{self.kwargs['pk']}/"
                )
        except KeyError as err:
            message = f"Failed to detect Status Server URL for {view_model} from {self.kwargs=}"
            raise RuntimeError(message) from err

        if not url:
            message = f"Failed to detect Status Server URL for {view_model} from {self.kwargs=}"
            raise RuntimeError(message)

        return {**context, "status": get_raw_status(url=url)}


# Parent extractor helpers


class UndetectableParentError(RuntimeError):
    ...


class UndetectableHostGroupError(RuntimeError):
    ...


class NonExistingError(NotFound):
    ...


class NonExistingParentError(NonExistingError):
    ...


class NonExistingHostGroupError(NonExistingError):
    ...


def extract_core_object_from_lookup_kwargs(**kwargs) -> CoreObjectDescriptor:
    lookup_keys = set(kwargs.keys())
    extra_filter: dict = {}

    if lookup_keys.issuperset({"component_pk", "service_pk", "cluster_pk"}):
        parent = CoreObjectDescriptor(id=int(kwargs["component_pk"]), type=ADCMCoreType.COMPONENT)
        extra_filter = {"service_id": kwargs["service_pk"], "cluster_id": kwargs["cluster_pk"]}

    elif lookup_keys.issuperset({"service_pk", "cluster_pk"}):
        parent = CoreObjectDescriptor(id=int(kwargs["service_pk"]), type=ADCMCoreType.SERVICE)
        extra_filter = {"cluster_id": kwargs["cluster_pk"]}

    elif lookup_keys.issuperset({"provider_pk"}):
        parent = CoreObjectDescriptor(id=int(kwargs["provider_pk"]), type=ADCMCoreType.PROVIDER)

    elif lookup_keys.issuperset({"host_pk"}):
        parent = CoreObjectDescriptor(id=int(kwargs["host_pk"]), type=ADCMCoreType.HOST)
        if "cluster_pk" in lookup_keys:
            extra_filter = {"cluster_id": kwargs["cluster_pk"]}

    elif lookup_keys.issuperset({"cluster_pk"}):
        parent = CoreObjectDescriptor(id=int(kwargs["cluster_pk"]), type=ADCMCoreType.CLUSTER)

    else:
        message = "Failed to detect core parent based on given arguments"
        raise UndetectableParentError(message)

    if not core_type_to_model(parent.type).objects.filter(id=parent.id, **extra_filter).exists():
        raise NonExistingParentError()

    return parent


def extract_host_group_from_lookup_kwargs_and_parent(parent: CoreObjectDescriptor, **kwargs) -> HostGroupDescriptor:
    if "config_host_group_pk" in kwargs:
        host_group = HostGroupDescriptor(id=int(kwargs["config_host_group_pk"]), type=ADCMHostGroupType.CONFIG)
    elif "action_host_group_pk" in kwargs:
        host_group = HostGroupDescriptor(id=int(kwargs["action_host_group_pk"]), type=ADCMHostGroupType.ACTION)
    else:
        message = "Failed to detect core parent based on given arguments"
        raise UndetectableHostGroupError(message)

    object_type = ContentType.objects.get_for_model(core_type_to_model(core_type=parent.type))
    if (
        not host_group_type_to_model(host_group_type=host_group.type)
        .objects.filter(id=host_group.id, object_id=parent.id, object_type=object_type)
        .exists()
    ):
        raise NonExistingHostGroupError()

    return host_group


def with_parent_object(func: Callable) -> Callable:
    """
    Decorator to extract "parent" object from kwargs (request lookup kwargs):
      - parent is presented as instance of `CoreObjectDescriptor`
      - if object is extracted and presented in DB, it is placed to a "parent" argument of wrapped func
      - otherwise, an exception will be raised that descends from DRF's `NotFound`

    If you'll need to put extracted parent not in "parent" kwarg,
    make this function accepting arguments and let user specify where to put it.

    If you'll need to not raise exception or raise another one,
    make this function accepting callable in arguments that'll decide what to do,
    then call in after catching the `NotFound` descendant exception.
    """

    @wraps(func)
    def wrapped(*args, **kwargs):
        parent = extract_core_object_from_lookup_kwargs(**kwargs)

        return func(*args, parent=parent, **kwargs)

    return wrapped


def with_group_object(func: Callable) -> Callable:
    """
    Same as `with_parent_object`, but detects Action/Config Host Group and puts it to "host_group" argument.
    Parent detection and existence will be checked too.
    It'll be ensured that group is part of parent

    Should be used like:

    class SomeViewSet:
        @with_group_object
        def post(self, request, *args, parent: CoreObjectDescriptor, host_group: HostGroupDescriptor, **kwargs):
            ...
    """

    @wraps(func)
    def wrapped(*args, **kwargs):
        parent = extract_core_object_from_lookup_kwargs(**kwargs)
        host_group = extract_host_group_from_lookup_kwargs_and_parent(parent=parent, **kwargs)

        return func(*args, parent=parent, host_group=host_group, **kwargs)

    return wrapped

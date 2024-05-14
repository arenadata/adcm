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

from typing import Collection

from cm.models import Cluster, ClusterObject, Host, ServiceComponent
from cm.services.status.client import retrieve_status_map
from cm.status_api import get_raw_status
from djangorestframework_camel_case.parser import (
    CamelCaseFormParser,
    CamelCaseJSONParser,
    CamelCaseMultiPartParser,
)
from djangorestframework_camel_case.render import (
    CamelCaseBrowsableAPIRenderer,
    CamelCaseJSONRenderer,
)
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
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
        "hostproviders": "hostprovider-list",
        "prototypes": "prototype-list",
        "jobs": "joblog-list",
        "tasks": "tasklog-list",
        "rbac": "rbac:root",
        "versions": "versions",
    }


class CamelCaseBrowsableAPIRendererWithoutForms(CamelCaseBrowsableAPIRenderer):
    """Renders the browsable api, but excludes the forms."""

    def get_context(self, *args, **kwargs):
        ctx = super().get_context(*args, **kwargs)
        ctx["post_form"] = False
        ctx["put_form"] = False
        return ctx


class CamelCaseGenericViewSet(GenericViewSet):
    parser_classes = [CamelCaseJSONParser, CamelCaseMultiPartParser, CamelCaseFormParser]
    renderer_classes = [CamelCaseJSONRenderer, CamelCaseBrowsableAPIRendererWithoutForms]


class CamelCaseModelViewSet(
    CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, ListModelMixin, CamelCaseGenericViewSet
):
    pass


class CamelCaseReadOnlyModelViewSet(RetrieveModelMixin, ListModelMixin, CamelCaseGenericViewSet):
    pass


class ObjectWithStatusViewMixin(GenericViewSet):
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
            elif view_model == ClusterObject:
                url = f"cluster/{self.kwargs['cluster_pk']}/service/{self.kwargs['pk']}/"
            elif view_model == ServiceComponent:
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

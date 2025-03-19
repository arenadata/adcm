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


import os

from adcm.feature_flags import use_new_bundle_parsing_approach
from adcm.permissions import DjangoObjectPermissionsAudit, IsAuthenticatedAudit
from audit.utils import audit
from cm.api import accept_license, get_license
from cm.bundle import delete_bundle, load_bundle, update_bundle, upload_file
from cm.models import (
    Action,
    Bundle,
    Prototype,
    PrototypeConfig,
    PrototypeExport,
    PrototypeImport,
    Upgrade,
)
from cm.services.adcm import adcm_config, get_adcm_config_id
from cm.services.bundle_alt.load import Directories, parse_bundle_archive
from cm.services.status.notify import reset_hc_map, reset_objects_in_mm
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.schemas.coreapi import AutoSchema
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from rest_framework.viewsets import ModelViewSet

from api.action.serializers import StackActionSerializer
from api.base_view import GenericUIViewSet, ModelPermOrReadOnlyForAuth
from api.stack.serializers import (
    ADCMPrototypeDetailSerializer,
    ADCMPrototypeSerializer,
    BundleSerializer,
    BundleServiceUIPrototypeSerializer,
    ClusterPrototypeDetailSerializer,
    ClusterPrototypeSerializer,
    ComponentPrototypeDetailSerializer,
    ComponentPrototypeSerializer,
    ComponentPrototypeUISerializer,
    HostPrototypeDetailSerializer,
    HostPrototypeSerializer,
    LoadBundleSerializer,
    PrototypeDetailSerializer,
    PrototypeSerializer,
    PrototypeUISerializer,
    ProviderPrototypeDetailSerializer,
    ProviderPrototypeSerializer,
    ServiceDetailPrototypeSerializer,
    ServicePrototypeSerializer,
    UploadBundleSerializer,
)
from api.utils import check_obj


@csrf_exempt
def load_servicemap_view(request: Request) -> HttpResponse:
    if request.method != "PUT":
        return HttpResponse(status=HTTP_405_METHOD_NOT_ALLOWED)

    reset_hc_map()
    reset_objects_in_mm()

    return HttpResponse(status=HTTP_200_OK)


class PrototypeRetrieveViewSet(RetrieveModelMixin, GenericUIViewSet):
    def get_object(self):
        instance = super().get_object()
        instance.actions = []
        for adcm_action in Action.objects.filter(prototype__id=instance.id):
            adcm_action.config = PrototypeConfig.objects.filter(
                prototype__id=instance.id,
                action=adcm_action,
            )
            instance.actions.append(adcm_action)

        instance.config = PrototypeConfig.objects.filter(prototype=instance, action=None)
        instance.imports = PrototypeImport.objects.filter(prototype=instance)
        instance.exports = PrototypeExport.objects.filter(prototype=instance)
        instance.upgrade = Upgrade.objects.filter(bundle=instance.bundle)

        return instance

    def retrieve(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(serializer.data)


class CsrfOffSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):  # noqa: ARG002
        return


class UploadBundleView(CreateModelMixin, GenericUIViewSet):
    queryset = Bundle.objects.all()
    serializer_class = UploadBundleSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    authentication_classes = (CsrfOffSessionAuthentication, TokenAuthentication)
    parser_classes = (MultiPartParser,)
    ordering = ["id"]

    @audit
    def create(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        upload_file(file=request.data["file"])
        return Response(status=HTTP_201_CREATED)


class LoadBundleView(CreateModelMixin, GenericUIViewSet):
    queryset = Bundle.objects.all()
    serializer_class = LoadBundleSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    ordering = ["id"]

    @audit
    def create(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        use_new_approach = use_new_bundle_parsing_approach(env=os.environ, headers=request.headers)
        func = self._new_create if use_new_approach else self._old_create

        result = func(serializer.validated_data["bundle_file"])

        return Response(BundleSerializer(result, context={"request": request}).data)

    def _old_create(self, file_path) -> Bundle:
        return load_bundle(bundle_file=str(file_path))

    def _new_create(self, file_path) -> Bundle:
        archive_in_downloads = settings.DOWNLOAD_DIR / file_path
        verified_signature_only = adcm_config(get_adcm_config_id()).config["global"]["accept_only_verified_bundles"]
        directories = Directories(downloads=settings.DOWNLOAD_DIR, bundles=settings.BUNDLE_DIR, files=settings.FILE_DIR)

        return parse_bundle_archive(
            archive=archive_in_downloads,
            directories=directories,
            adcm_version=settings.ADCM_VERSION,
            verified_signature_only=verified_signature_only,
        )


class BundleViewSet(ModelViewSet):
    queryset = Bundle.objects.all()
    serializer_class = BundleSerializer
    filterset_fields = ("name", "version")
    ordering_fields = ("id", "name", "version_order")
    lookup_url_kwarg = "bundle_pk"
    schema = AutoSchema()

    ordering = ["id"]

    def get_permissions(self):
        permission_classes = (IsAuthenticated,) if self.action == "list" else (ModelPermOrReadOnlyForAuth,)

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if self.action == "list":
            return Bundle.objects.exclude(hash="adcm")

        return super().get_queryset()

    @audit
    def destroy(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        bundle = self.get_object()
        delete_bundle(bundle)

        return Response(status=HTTP_204_NO_CONTENT)

    @audit
    @action(methods=["put"], detail=True)
    def update_bundle(self, request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        bundle = check_obj(Bundle, kwargs["bundle_pk"], "BUNDLE_NOT_FOUND")
        update_bundle(bundle)
        serializer = self.get_serializer(bundle)

        return Response(serializer.data)

    @staticmethod
    @action(methods=["get"], detail=True)
    def license(request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002, ARG004
        bundle = check_obj(Bundle, kwargs["bundle_pk"], "BUNDLE_NOT_FOUND")
        proto = Prototype.objects.filter(bundle=bundle, name=bundle.name).first()
        body = get_license(proto)
        url = reverse(viewname="v1:accept-license", kwargs={"prototype_pk": proto.pk}, request=request)

        return Response({"license": proto.license, "accept": url, "text": body})

    @audit
    @action(methods=["put"], detail=True)
    def accept_license(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        # self is necessary for audit

        bundle = check_obj(Bundle, kwargs["bundle_pk"], "BUNDLE_NOT_FOUND")
        proto = Prototype.objects.filter(bundle=bundle, name=bundle.name).first()
        accept_license(proto)

        return Response()


class PrototypeViewSet(ListModelMixin, PrototypeRetrieveViewSet):
    queryset = Prototype.objects.all()
    serializer_class = PrototypeSerializer
    filterset_fields = ("name", "bundle_id", "license")
    ordering_fields = ("display_name", "version_order")
    lookup_url_kwarg = "prototype_pk"
    ordering = ["id"]

    def get_permissions(self):
        permission_classes = (IsAuthenticated,) if self.action == "list" else (ModelPermOrReadOnlyForAuth,)
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.is_for_ui():
            return PrototypeUISerializer
        elif self.action == "retrieve":
            return PrototypeDetailSerializer

        return super().get_serializer_class()

    @staticmethod
    @action(methods=["get"], detail=True)
    def license(request: Request, *args, **kwargs) -> Response:  # noqa: ARG002, ARG004
        prototype = check_obj(Prototype, kwargs["prototype_pk"], "PROTOTYPE_NOT_FOUND")
        body = get_license(prototype)
        url = reverse(viewname="v1:accept-license", kwargs={"prototype_pk": prototype.pk}, request=request)

        return Response({"license": prototype.license, "accept": url, "text": body})

    @audit
    @action(methods=["put"], detail=True)
    def accept_license(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        # self is necessary for audit

        prototype = check_obj(Prototype, kwargs["prototype_pk"], "PROTOTYPE_NOT_FOUND")
        accept_license(prototype)

        return Response()


class ProtoActionViewSet(RetrieveModelMixin, GenericUIViewSet):
    queryset = Action.objects.all()
    serializer_class = StackActionSerializer
    lookup_url_kwarg = "action_pk"
    ordering = ["id"]

    def retrieve(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        obj = check_obj(Action, kwargs["action_pk"], "ACTION_NOT_FOUND")
        serializer = self.get_serializer(obj)

        return Response(serializer.data)


class ServicePrototypeViewSet(ListModelMixin, RetrieveModelMixin, GenericUIViewSet):
    queryset = Prototype.objects.filter(type="service")
    serializer_class = ServicePrototypeSerializer
    filterset_fields = ("name", "bundle_id", "license")
    ordering_fields = ("display_name", "version_order")
    lookup_url_kwarg = "prototype_pk"

    def get_serializer_class(self):
        if self.is_for_ui():
            return BundleServiceUIPrototypeSerializer
        if self.action == "retrieve":
            return ServiceDetailPrototypeSerializer
        elif self.action == "action":
            return StackActionSerializer

        return super().get_serializer_class()

    def retrieve(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        instance = self.get_object()
        instance.actions = Action.objects.filter(prototype__type="service", prototype__pk=instance.pk)
        instance.component_prototypes = Prototype.objects.filter(parent=instance, type="component")
        instance.config = PrototypeConfig.objects.filter(prototype=instance, action=None).order_by("id")
        instance.exports = PrototypeExport.objects.filter(prototype=instance)
        instance.imports = PrototypeImport.objects.filter(prototype=instance)
        serializer = self.get_serializer(instance)

        return Response(serializer.data)

    @action(methods=["get"], detail=True)
    def actions(self, request: Request, prototype_pk: int) -> Response:  # noqa: ARG001, ARG002
        return Response(
            StackActionSerializer(
                Action.objects.filter(prototype__type="service", prototype_id=prototype_pk),
                many=True,
            ).data,
        )


class ComponentPrototypeViewSet(ListModelMixin, PrototypeRetrieveViewSet):
    queryset = Prototype.objects.filter(type="component")
    serializer_class = ComponentPrototypeSerializer
    filterset_fields = ("name", "bundle_id")
    ordering_fields = ("display_name", "version_order")
    lookup_url_kwarg = "prototype_pk"

    def get_serializer_class(self):
        if self.is_for_ui():
            return ComponentPrototypeUISerializer
        if self.action == "retrieve":
            return ComponentPrototypeDetailSerializer

        return super().get_serializer_class()


class ProviderPrototypeViewSet(ListModelMixin, PrototypeRetrieveViewSet):
    queryset = Prototype.objects.filter(type="provider")
    serializer_class = ProviderPrototypeSerializer
    filterset_fields = ("name", "bundle_id")
    ordering_fields = ("display_name", "version_order")
    permission_classes = (IsAuthenticatedAudit,)
    lookup_url_kwarg = "prototype_pk"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProviderPrototypeDetailSerializer

        return super().get_serializer_class()


class HostPrototypeViewSet(ListModelMixin, PrototypeRetrieveViewSet):
    queryset = Prototype.objects.filter(type="host")
    serializer_class = HostPrototypeSerializer
    filterset_fields = ("name", "bundle_id")
    ordering_fields = ("display_name", "version_order")
    lookup_url_kwarg = "prototype_pk"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return HostPrototypeDetailSerializer

        return super().get_serializer_class()


class ClusterPrototypeViewSet(ListModelMixin, PrototypeRetrieveViewSet):
    queryset = Prototype.objects.filter(type="cluster")
    serializer_class = ClusterPrototypeSerializer
    filterset_fields = ("name", "bundle_id", "display_name")
    ordering_fields = ("display_name", "version_order", "version")
    lookup_url_kwarg = "prototype_pk"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ClusterPrototypeDetailSerializer

        return super().get_serializer_class()


class ADCMPrototypeViewSet(ListModelMixin, PrototypeRetrieveViewSet):
    queryset = Prototype.objects.filter(type="adcm")
    serializer_class = ADCMPrototypeSerializer
    filterset_fields = ("bundle_id",)
    lookup_url_kwarg = "prototype_pk"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ADCMPrototypeDetailSerializer

        return super().get_serializer_class()

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

from pathlib import Path

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
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import DjangoObjectPermissionsAudit, IsAuthenticatedAudit
from api.action.serializers import StackActionSerializer
from api.base_view import GenericUIViewSet, ModelPermOrReadOnlyForAuth
from api.stack.serializers import (
    ADCMPrototypeDetailSerializer,
    ADCMPrototypeSerializer,
    BundleSerializer,
    ClusterPrototypeDetailSerializer,
    ClusterPrototypeSerializer,
    ComponentPrototypeDetailSerializer,
    ComponentPrototypeSerializer,
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
from audit.utils import audit
from cm.api import accept_license, get_license, load_service_map
from cm.bundle import delete_bundle, load_bundle, update_bundle
from cm.models import (
    Action,
    Bundle,
    Prototype,
    PrototypeConfig,
    PrototypeExport,
    PrototypeImport,
    Upgrade,
)


@csrf_exempt
def load_servicemap_view(request: Request) -> HttpResponse:
    if request.method != "PUT":
        return HttpResponse(status=HTTP_405_METHOD_NOT_ALLOWED)

    load_service_map()

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

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(serializer.data)


class CsrfOffSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


class UploadBundleView(CreateModelMixin, GenericUIViewSet):
    queryset = Bundle.objects.all()
    serializer_class = UploadBundleSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    authentication_classes = (CsrfOffSessionAuthentication, TokenAuthentication)
    parser_classes = (MultiPartParser,)

    @audit
    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        fd = request.data["file"]
        with open(Path(settings.DOWNLOAD_DIR, fd.name), "wb+") as f:
            for chunk in fd.chunks():
                f.write(chunk)

        return Response(status=HTTP_201_CREATED)


class LoadBundleView(CreateModelMixin, GenericUIViewSet):
    queryset = Bundle.objects.all()
    serializer_class = LoadBundleSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)

    @audit
    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        return Response(
            BundleSerializer(load_bundle(serializer.validated_data["bundle_file"]), context={"request": request}).data,
        )


class BundleViewSet(ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Bundle.objects.all()
    serializer_class = BundleSerializer
    filterset_fields = ("name", "version")
    ordering_fields = ("name", "version_order")
    lookup_url_kwarg = "bundle_pk"

    def get_permissions(self):
        if self.action == "list":
            permission_classes = (IsAuthenticated,)
        else:
            permission_classes = (ModelPermOrReadOnlyForAuth,)

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if self.action == "list":
            return Bundle.objects.exclude(hash="adcm")

        return super().get_queryset()

    @audit
    def destroy(self, request, *args, **kwargs) -> Response:
        bundle = self.get_object()
        delete_bundle(bundle)

        return Response(status=HTTP_204_NO_CONTENT)

    @audit
    @action(methods=["put"], detail=True)
    def update_bundle(self, request, *args, **kwargs) -> Response:
        bundle = check_obj(Bundle, kwargs["bundle_pk"], "BUNDLE_NOT_FOUND")
        update_bundle(bundle)
        serializer = self.get_serializer(bundle)

        return Response(serializer.data)

    @staticmethod
    @action(methods=["get"], detail=True)
    def license(request, *args, **kwargs) -> Response:
        bundle = check_obj(Bundle, kwargs["bundle_pk"], "BUNDLE_NOT_FOUND")
        proto = Prototype.objects.filter(bundle=bundle, name=bundle.name).first()
        body = get_license(proto)
        url = reverse(viewname="accept-license", kwargs={"prototype_pk": proto.pk}, request=request)
        return Response({"license": proto.license, "accept": url, "text": body})

    @audit
    @action(methods=["put"], detail=True)
    def accept_license(self, request: Request, *args, **kwargs) -> Response:
        # self is necessary for audit

        bundle = check_obj(Bundle, kwargs["bundle_pk"], "BUNDLE_NOT_FOUND")
        proto = Prototype.objects.filter(bundle=bundle, name=bundle.name).first()
        accept_license(proto)

        return Response()


#  pylint:disable-next=too-many-ancestors
class PrototypeViewSet(ListModelMixin, PrototypeRetrieveViewSet):
    queryset = Prototype.objects.all()
    serializer_class = PrototypeSerializer
    filterset_fields = ("name", "bundle_id")
    ordering_fields = ("display_name", "version_order")
    lookup_url_kwarg = "prototype_pk"

    def get_permissions(self):
        if self.action == "list":
            permission_classes = (IsAuthenticated,)
        else:
            permission_classes = (ModelPermOrReadOnlyForAuth,)

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.is_for_ui():
            return PrototypeUISerializer
        elif self.action == "retrieve":
            return PrototypeDetailSerializer

        return super().get_serializer_class()

    @staticmethod
    @action(methods=["get"], detail=True)
    def license(request: Request, *args, **kwargs) -> Response:
        prototype = check_obj(Prototype, kwargs["prototype_pk"], "PROTOTYPE_NOT_FOUND")
        body = get_license(prototype)
        url = reverse(viewname="accept-license", kwargs={"prototype_pk": prototype.pk}, request=request)

        return Response({"license": prototype.license, "accept": url, "text": body})

    @audit
    @action(methods=["put"], detail=True)
    def accept_license(self, request: Request, *args, **kwargs) -> Response:
        # self is necessary for audit

        prototype = check_obj(Prototype, kwargs["prototype_pk"], "PROTOTYPE_NOT_FOUND")
        accept_license(prototype)

        return Response()


class ProtoActionViewSet(RetrieveModelMixin, GenericUIViewSet):
    queryset = Action.objects.all()
    serializer_class = StackActionSerializer
    lookup_url_kwarg = "action_pk"

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        obj = check_obj(Action, kwargs["action_pk"], "ACTION_NOT_FOUND")
        serializer = self.get_serializer(obj)

        return Response(serializer.data)


#  pylint:disable-next=too-many-ancestors
class ServicePrototypeViewSet(ListModelMixin, RetrieveModelMixin, GenericUIViewSet):
    queryset = Prototype.objects.filter(type="service")
    serializer_class = ServicePrototypeSerializer
    filterset_fields = ("name", "bundle_id")
    ordering_fields = ("display_name", "version_order")
    lookup_url_kwarg = "prototype_pk"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ServiceDetailPrototypeSerializer
        elif self.action == "action":
            return StackActionSerializer

        return super().get_serializer_class()

    def retrieve(self, request, *args, **kwargs) -> Response:
        instance = self.get_object()
        instance.actions = Action.objects.filter(prototype__type="service", prototype__pk=instance.pk)
        instance.components = Prototype.objects.filter(parent=instance, type="component")
        instance.config = PrototypeConfig.objects.filter(prototype=instance, action=None).order_by("id")
        instance.exports = PrototypeExport.objects.filter(prototype=instance)
        instance.imports = PrototypeImport.objects.filter(prototype=instance)
        serializer = self.get_serializer(instance)

        return Response(serializer.data)

    @action(methods=["get"], detail=True)
    def actions(self, request: Request, prototype_pk: int) -> Response:
        return Response(
            StackActionSerializer(
                Action.objects.filter(prototype__type="service", prototype_id=prototype_pk),
                many=True,
            ).data,
        )


#  pylint:disable-next=too-many-ancestors
class ComponentPrototypeViewSet(ListModelMixin, PrototypeRetrieveViewSet):
    queryset = Prototype.objects.filter(type="component")
    serializer_class = ComponentPrototypeSerializer
    filterset_fields = ("name", "bundle_id")
    ordering_fields = ("display_name", "version_order")
    lookup_url_kwarg = "prototype_pk"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ComponentPrototypeDetailSerializer

        return super().get_serializer_class()


#  pylint:disable-next=too-many-ancestors
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


#  pylint:disable-next=too-many-ancestors
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


#  pylint:disable-next=too-many-ancestors
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

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != "list":
            return queryset

        pks = set()
        field_names = self.request.query_params.get("fields")
        distinct = self.request.query_params.get("distinct")
        if field_names and distinct:
            for field_name in field_names.split(","):
                values_list = queryset.values(field_name, "pk")
                if not values_list:
                    continue

                field_value = values_list[0][field_name]
                pks.add(values_list[0]["pk"])
                if len(values_list) == 1:
                    continue

                for value in values_list[1:]:
                    if value[field_name] != field_value:
                        pks.add(value["pk"])

        if pks:
            return queryset.filter(pk__in=pks)

        return queryset


#  pylint:disable-next=too-many-ancestors
class ADCMPrototypeViewSet(ListModelMixin, PrototypeRetrieveViewSet):
    queryset = Prototype.objects.filter(type="adcm")
    serializer_class = ADCMPrototypeSerializer
    filterset_fields = ("bundle_id",)
    lookup_url_kwarg = "prototype_pk"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ADCMPrototypeDetailSerializer

        return super().get_serializer_class()

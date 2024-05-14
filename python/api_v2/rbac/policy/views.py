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

from adcm.permissions import VIEW_POLICY_PERMISSION, CustomModelPermissionsByMethod
from audit.utils import audit
from cm.errors import AdcmEx, raise_adcm_ex
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rbac.models import Policy
from rbac.services.policy import policy_create, policy_update
from rest_framework.exceptions import NotFound
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import DefaultParams, ErrorSerializer
from api_v2.rbac.policy.filters import PolicyFilter
from api_v2.rbac.policy.serializers import PolicyCreateSerializer, PolicySerializer, PolicyUpdateSerializer
from api_v2.views import CamelCaseGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getPolicies",
        description="Get information about ADCM policies.",
        summary="GET policies",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(name="name", description="Case insensitive and partial filter by policy name."),
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                type=str,
                enum=("name", "-name"),
                default="name",
            ),
        ],
        responses={
            HTTP_200_OK: PolicySerializer(many=True),
            HTTP_403_FORBIDDEN: ErrorSerializer,
        },
    ),
    create=extend_schema(
        operation_id="postPolicies",
        description="Create a new ADCM policy.",
        summary="POST policies",
        responses={
            HTTP_201_CREATED: PolicySerializer(many=False),
            **{err_code: ErrorSerializer for err_code in (HTTP_403_FORBIDDEN, HTTP_409_CONFLICT, HTTP_400_BAD_REQUEST)},
        },
    ),
    retrieve=extend_schema(
        operation_id="getPolicy",
        description="Get information about a specific ADCM policy.",
        summary="GET policy",
        responses={
            HTTP_200_OK: PolicySerializer(many=False),
            **{err_code: ErrorSerializer for err_code in (HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN)},
        },
    ),
    partial_update=extend_schema(
        operation_id="patchPolicy",
        description="Change information on a specific ADCM policy.",
        summary="PATCH policy",
        responses={
            HTTP_200_OK: PolicySerializer(many=False),
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_403_FORBIDDEN, HTTP_409_CONFLICT, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND)
            },
        },
    ),
    destroy=extend_schema(
        operation_id="deletePolicy",
        description="Delete specific ADCM policy.",
        summary="DELETE policy",
        responses={
            HTTP_204_NO_CONTENT: None,
            **{err_code: ErrorSerializer for err_code in (HTTP_409_CONFLICT, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)},
        },
    ),
)
class PolicyViewSet(
    PermissionListMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    CreateModelMixin,
    CamelCaseGenericViewSet,
):
    queryset = Policy.objects.select_related("role").prefetch_related("group", "object").order_by("name")
    filter_backends = (DjangoFilterBackend,)
    filterset_class = PolicyFilter
    permission_classes = (CustomModelPermissionsByMethod,)
    method_permissions_map = {
        "patch": [(VIEW_POLICY_PERMISSION, NotFound)],
        "delete": [(VIEW_POLICY_PERMISSION, NotFound)],
    }
    permission_required = [VIEW_POLICY_PERMISSION]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self) -> type[PolicySerializer | PolicyCreateSerializer | PolicyUpdateSerializer]:
        if self.action == "create":
            return PolicyCreateSerializer

        if self.action == "partial_update":
            return PolicyUpdateSerializer

        return PolicySerializer

    @audit
    def create(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = policy_create(**serializer.validated_data)
        return Response(data=PolicySerializer(policy).data, status=HTTP_201_CREATED)

    @audit
    def partial_update(self, request, *args, **kwargs):  # noqa: ARG002
        policy = self.get_object()

        if policy.built_in:
            raise AdcmEx(code="POLICY_CREATE_ERROR")

        serializer = self.get_serializer(policy, data=request.data, partial=kwargs.pop("partial", False))
        serializer.is_valid(raise_exception=True)
        policy = policy_update(policy, **serializer.validated_data)
        return Response(data=PolicySerializer(policy).data)

    @audit
    def destroy(self, request, *args, **kwargs):
        policy = self.get_object()
        if policy.built_in:
            return raise_adcm_ex(code="POLICY_DELETE_ERROR")

        return super().destroy(request, *args, **kwargs)

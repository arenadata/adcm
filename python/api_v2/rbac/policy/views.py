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

from collections.abc import Iterable

from adcm.permissions import VIEW_POLICY_PERMISSION
from audit.alt.api import audit_create, audit_delete, audit_update
from audit.alt.hooks import (
    extract_current_from_response,
    extract_from_object,
    extract_previous_from_object,
    only_on_success,
)
from cm.converters import model_name_to_core_type
from cm.errors import AdcmEx
from cm.transition.status import StatusScenarios
from core.object.repo import ObjectRepoI
from core.object.types import Selector
from core.types import CoreObjectDescriptor
from dishka import FromDishka
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rbac.models import Policy, PolicyObject
from rbac.services.policy import policy_create, policy_update
from rest_framework.mixins import DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import DefaultParams, responses
from api_v2.rbac.policy.filters import PolicyFilter
from api_v2.rbac.policy.permissions import PolicyPermissions
from api_v2.rbac.policy.serializers import (
    PolicyCreateSerializer,
    PolicySerializer,
    PolicyUpdateSerializer,
    SchemaPolicySerializer,
)
from api_v2.utils.audit import (
    policy_from_lookup,
    policy_from_response,
    retrieve_policy_role_object_group,
    update_policy_name,
)
from api_v2.utils.di import inject
from api_v2.views import ADCMGenericViewSet


def _object_selectors(
    object_repo: ObjectRepoI,
    policies: Policy | Iterable[Policy],
) -> dict[tuple[int, int], Selector]:
    if isinstance(policies, Policy):
        policies = (policies,)

    policy_ids = [policy.pk for policy in policies]
    policy_object_fields = list(
        PolicyObject.objects.filter(policy__in=policy_ids)
        .values_list("content_type_id", "object_id", "content_type__model")
        .distinct()
    )

    keys = [(content_type_id, object_id) for content_type_id, object_id, _ in policy_object_fields]
    targets = [
        CoreObjectDescriptor(id=object_id, type=model_name_to_core_type(model_name))
        for _, object_id, model_name in policy_object_fields
    ]
    selectors = object_repo.build_selector(targets=targets)

    return {key: selectors[target] for key, target in zip(keys, targets, strict=True)}


@extend_schema_view(
    list=extend_schema(
        operation_id="getPolicies",
        description="Get information about ADCM policies.",
        summary="GET policies",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=("name", "-name", "roleName", "-roleName", "roleDisplayName", "-roleDisplayName"),
                default="name",
            ),
        ],
        responses=responses(success=SchemaPolicySerializer(many=True)),
    ),
    create=extend_schema(
        operation_id="postPolicies",
        description="Create a new ADCM policy.",
        summary="POST policies",
        responses=responses(
            success=(HTTP_201_CREATED, SchemaPolicySerializer),
            errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    ),
    retrieve=extend_schema(
        operation_id="getPolicy",
        description="Get information about a specific ADCM policy.",
        summary="GET policy",
        responses=responses(success=SchemaPolicySerializer, errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)),
    ),
    partial_update=extend_schema(
        operation_id="patchPolicy",
        description="Change information on a specific ADCM policy.",
        summary="PATCH policy",
        responses=responses(
            success=SchemaPolicySerializer, errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
        ),
    ),
    destroy=extend_schema(
        operation_id="deletePolicy",
        description="Delete specific ADCM policy.",
        summary="DELETE policy",
        responses=responses(
            success=(HTTP_204_NO_CONTENT, None), errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
        ),
    ),
)
class PolicyViewSet(PermissionListMixin, DestroyModelMixin, ADCMGenericViewSet):
    queryset = (
        Policy.objects.select_related("role")
        .prefetch_related("group", "object", "object__object", "object__object__prototype")
        .order_by("name")
    )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = PolicyFilter
    permission_classes = (IsAuthenticated, PolicyPermissions)
    permission_required = [VIEW_POLICY_PERMISSION]

    def get_serializer_class(self) -> type[PolicySerializer | PolicyCreateSerializer | PolicyUpdateSerializer]:
        if self.action == "create":
            return PolicyCreateSerializer

        if self.action == "partial_update":
            return PolicyUpdateSerializer

        return PolicySerializer

    @inject
    def list(
        self,
        request,  # noqa: ARG002
        *,
        object_repo: FromDishka[ObjectRepoI],
        **_,
    ) -> Response:
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        policies = page if page is not None else queryset
        context = {**self.get_serializer_context(), "object_selectors": _object_selectors(object_repo, policies)}
        serializer = self.get_serializer(policies, many=True, context=context)

        if page is not None:
            return self.get_paginated_response(serializer.data)

        return Response(serializer.data)

    @inject
    def retrieve(
        self,
        request,  # noqa: ARG002
        *,
        object_repo: FromDishka[ObjectRepoI],
        **_,
    ) -> Response:
        instance = self.get_object()
        context = {**self.get_serializer_context(), "object_selectors": _object_selectors(object_repo, instance)}
        serializer = self.get_serializer(instance, context=context)

        return Response(serializer.data)

    @audit_create(name="Policy created", object_=policy_from_response)
    @inject
    def create(
        self,
        request,
        *,
        object_repo: FromDishka[ObjectRepoI],
        **_,
    ) -> Response:
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = policy_create(**serializer.validated_data)
        context = {**self.get_serializer_context(), "object_selectors": _object_selectors(object_repo, policy)}
        return Response(data=PolicySerializer(policy, context=context).data, status=HTTP_201_CREATED)

    @(
        audit_update(name="Policy updated", object_=policy_from_lookup)
        .attach_hooks(on_collect=only_on_success(update_policy_name))
        .track_changes(
            before=(
                extract_previous_from_object(Policy, "name", "description"),
                extract_from_object(func=retrieve_policy_role_object_group, section="previous"),
            ),
            after=(
                extract_current_from_response("name", "description"),
                extract_from_object(func=retrieve_policy_role_object_group, section="current"),
            ),
        )
    )
    @inject
    def partial_update(
        self,
        request,
        *,
        status_scenarios: FromDishka[StatusScenarios],
        object_repo: FromDishka[ObjectRepoI],
        **_,
    ) -> Response:
        policy = self.get_object()

        if policy.built_in:
            raise AdcmEx(code="POLICY_CREATE_ERROR")

        serializer = self.get_serializer(policy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        policy = policy_update(policy, status_scenarios=status_scenarios, **serializer.validated_data)
        context = {**self.get_serializer_context(), "object_selectors": _object_selectors(object_repo, policy)}
        return Response(data=PolicySerializer(policy, context=context).data)

    @audit_delete(name="Policy deleted", object_=policy_from_lookup, removed_on_success=True)
    def destroy(self, request, *args, **kwargs):
        policy = self.get_object()
        if policy.built_in:
            raise AdcmEx(code="POLICY_DELETE_ERROR")

        return super().destroy(request, *args, **kwargs)

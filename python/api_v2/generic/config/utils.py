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

from typing import TypeAlias

from cm.converters import orm_object_to_core_descriptor
from cm.models import (
    Cluster,
    Component,
    ConfigHostGroup,
    Host,
    Provider,
    Service,
)
from core.types import ADCMHostGroupType, Descriptor
from dishka import FromDishka
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND
import core

from api_v2.api_schema import DefaultParams, responses
from api_v2.utils.di import inject

ParentObject: TypeAlias = Cluster | Service | Component | Provider | Host | ConfigHostGroup


def extend_config_schema(type_: str):
    capitalized_type = type_.capitalize()
    return extend_schema(
        operation_id=f"get{capitalized_type}ConfigSchema",
        summary=f"GET {type_}'s config schema",
        description=f"Get {type_}'s config schema information.",
        examples=DefaultParams.CONFIG_SCHEMA_EXAMPLE,
        responses=responses(success=dict, errors=HTTP_404_NOT_FOUND),
    )


class ConfigSchemaMixin:
    @action(methods=["get"], detail=True, url_path="config-schema", url_name="config-schema")
    @inject
    def config_schema(self, request, config_service: FromDishka[core.config.ConfigService], **_) -> Response:
        instance = self.get_object()
        self._check_parent_permissions_in_config_schema(request=request, parent_object=instance)
        instance_config_view_perm = "cm.view_objectconfig"

        if not (
            request.user.has_perm(instance_config_view_perm, instance.config)
            or request.user.has_perm(instance_config_view_perm)
        ):
            raise PermissionDenied

        if isinstance(instance, ConfigHostGroup):
            owner_obj = instance.object
            if not owner_obj:
                message = f"Got group without owner: {instance}"
                raise RuntimeError(message)

            owner = core.config.HostGroupConfigOwner(
                descriptor=orm_object_to_core_descriptor(owner_obj),
                state=owner_obj.state,
                group=Descriptor(id=instance.pk, type=ADCMHostGroupType.CONFIG),
            )

        else:
            owner = core.config.ConfigOwner(
                descriptor=orm_object_to_core_descriptor(instance),
                state=instance.state,
            )

        schema = config_service.retrieve_jsonschema(owner=owner)

        return Response(data=schema, status=HTTP_200_OK)

    def _check_parent_permissions_in_config_schema(self, request: Request, parent_object: ParentObject | None):
        parent_view_perm = f"cm.view_{parent_object.__class__.__name__.lower()}"

        if parent_object is None:
            raise NotFound

        if not (request.user.has_perm(parent_view_perm, parent_object) or request.user.has_perm(parent_view_perm)):
            raise NotFound

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

from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, TypeAlias
import json

from cm.converters import orm_object_to_core_descriptor
from cm.legacy.adcm_config.config import get_default
from cm.legacy.services.bundle import PathResolver
from cm.legacy.variant import get_variant
from cm.models import (
    ADCMEntity,
    Cluster,
    Component,
    ConfigHostGroup,
    ConfigLog,
    Host,
    PrototypeConfig,
    Provider,
    Service,
)
from core.types import ADCMHostGroupType, Descriptor
from dishka import FromDishka
from django.db.models import QuerySet
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


class Field(ABC):
    def __init__(
        self, prototype_config: PrototypeConfig, object_: ADCMEntity | ConfigHostGroup, path_resolver: PathResolver
    ):
        self.object_ = object_
        self.is_host_group = False

        if isinstance(object_, ConfigHostGroup):
            self.is_host_group = True
            self.object_ = object_.object

        self.prototype_config = prototype_config

        self.name = prototype_config.name
        self.title = prototype_config.display_name
        self.description = prototype_config.description
        self.limits = self.prototype_config.limits
        self.required = self.prototype_config.required

        self._path_resolver = path_resolver

    @property
    @abstractmethod
    def type(self) -> str:
        ...

    @property
    def is_read_only(self) -> bool:
        if not self.limits:
            return False

        readonly = self.limits.get("read_only", [])
        writeable = self.limits.get("writable", [])

        if readonly == "any" or self.object_.state in readonly:
            return True

        if writeable == "any":
            return False

        if writeable and self.object_.state not in writeable:
            return True

        return False

    @property
    def is_advanced(self) -> bool:
        return self.prototype_config.ui_options.get("advanced", False)

    @property
    def is_invisible(self) -> bool:
        if self.prototype_config.name == "__main_info":
            return True

        return self.prototype_config.ui_options.get("invisible", False)

    @property
    def activation(self) -> dict | None:
        return None

    @property
    def synchronization(self) -> dict | None:
        if not self.is_host_group:
            return None

        is_allow_change = self.prototype_config.group_customization
        if is_allow_change is None:
            is_allow_change = self.object_.prototype.config_group_customization

        return {"isAllowChange": is_allow_change}

    @property
    def is_secret(self) -> bool:
        return False

    @property
    def string_extra(self) -> dict | None:
        return None

    @property
    def enum_extra(self) -> dict | None:
        return None

    @property
    def default(self) -> Any:
        return get_default(conf=self.prototype_config, path_resolver=self._path_resolver)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "type": self.type,
            "description": self.description,
            "default": self.default,
            "readOnly": self.is_read_only,
            "adcmMeta": {
                "isAdvanced": self.is_advanced,
                "isInvisible": self.is_invisible,
                "activation": self.activation,
                "synchronization": self.synchronization,
                "isSecret": self.is_secret,
                "stringExtra": self.string_extra,
                "enumExtra": self.enum_extra,
            },
        }


class Boolean(Field):
    type = "boolean"

    def to_dict(self) -> dict:
        data = super().to_dict()

        if not self.required:
            return {"oneOf": [data, {"type": "null"}]}

        return data


class Float(Field):
    type = "number"

    def to_dict(self) -> dict:
        data = super().to_dict()

        if "min" in self.limits:
            data.update({"minimum": self.limits["min"]})

        if "max" in self.limits:
            data.update({"maximum": self.limits["max"]})

        if not self.required:
            return {"oneOf": [data, {"type": "null"}]}

        return data


class Integer(Field):
    type = "integer"

    def to_dict(self) -> dict:
        data = super().to_dict()

        if "min" in self.limits:
            data.update({"minimum": self.limits["min"]})

        if "max" in self.limits:
            data.update({"maximum": self.limits["max"]})

        if not self.required:
            return {"oneOf": [data, {"type": "null"}]}

        return data


class String(Field):
    type = "string"

    @property
    def string_extra(self) -> dict | None:
        return {"isMultiline": False}

    def to_dict(self) -> dict:
        data = super().to_dict()

        if "pattern" in self.limits:
            data["pattern"] = self.limits["pattern"]

        if self.required:
            data.update({"minLength": 1})
        else:
            return {"oneOf": [data, {"type": "null"}]}

        return data


class Password(String):
    @property
    def is_secret(self) -> bool:
        return True


class Text(String):
    @property
    def string_extra(self) -> dict | None:
        return {"isMultiline": True}


class SecretText(Text):
    @property
    def is_secret(self) -> bool:
        return True


class File(Text):
    pass


class SecretFile(SecretText):
    pass


class Json(Field):
    type = "string"

    @property
    def string_extra(self) -> dict | None:
        return {"isMultiline": True}

    @property
    def default(self) -> Any:
        value = super().default

        return json.dumps(value) if value is not None else None

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({"format": "json"})

        if self.required:
            data.update({"minLength": 1})

        if not self.required:
            return {"oneOf": [data, {"type": "null"}]}

        return data


class Map(Field):
    type = "object"

    @property
    def default(self) -> Any:
        default = super().default

        if default is None:
            return {}

        return default

    def to_dict(self) -> dict:
        data = super().to_dict()

        data.update({"additionalProperties": True, "properties": {}})

        if self.required:
            data.update({"minProperties": 1})

        if not self.required:
            return {"oneOf": [data, {"type": "null"}]}

        return data


class SecretMap(Map):
    @property
    def is_secret(self) -> bool:
        return True


class Structure(Field):
    def __init__(
        self, prototype_config: PrototypeConfig, object_: ADCMEntity | ConfigHostGroup, path_resolver: PathResolver
    ):
        super().__init__(prototype_config=prototype_config, object_=object_, path_resolver=path_resolver)

        self.yspec = self.limits["yspec"]

    @staticmethod
    def _get_schema_type(type_: str) -> str:
        match type_:
            case "list":
                return "array"
            case "dict":
                return "object"
            case "bool":
                return "boolean"
            case "string":
                return "string"
            case "int":
                return "integer"
            case "float":
                return "number"
            case _:
                raise NotImplementedError

    @property
    def type(self) -> str:
        return self._get_schema_type(type_=self.yspec["root"]["match"])

    @property
    def default(self) -> Any:
        default = super().default

        if default is None:
            if self.type == "array":
                return []
            if self.type == "object":
                return {}

        return default

    def _get_inner(self, match: str, title: str = "", is_invisible: bool = False, **kwargs) -> dict:
        type_ = self._get_schema_type(type_=match)

        data = {
            "type": type_,
            "title": title,
            "description": "",
            "default": None,
            "readOnly": self.is_read_only,
            "adcmMeta": {
                "isAdvanced": self.is_advanced,
                "isInvisible": is_invisible,
                "activation": self.activation,
                "synchronization": None,
                "isSecret": self.is_secret,
                "stringExtra": self.string_extra,
                "enumExtra": self.enum_extra,
            },
        }

        if type_ == "array":
            data.update({"items": self._get_inner(**self.yspec[kwargs["item"]]), "default": []})

        elif type_ == "object":
            required_items: list[str] = kwargs.get("required_items", [])

            data.update(
                {
                    "additionalProperties": False,
                    "properties": {},
                    "required": required_items,
                    "default": {},
                }
            )

            invisible_items = kwargs.get("invisible_items", [])

            for item_key, item_value in kwargs["items"].items():
                is_invisible = item_key in invisible_items
                is_invisible = self.is_invisible if self.is_invisible else is_invisible
                entry_data = self._get_inner(title=item_key, is_invisible=is_invisible, **self.yspec[item_value])
                if entry_data["title"] not in required_items and entry_data["type"] not in ("array", "object"):
                    entry_data.pop("default", None)

                data["properties"][item_key] = entry_data

        return data

    def to_dict(self) -> dict:
        data = super().to_dict()

        type_ = self.type

        if type_ == "array":
            item = self.yspec["root"]["item"]
            data["items"] = self._get_inner(**self.yspec[item])

            if self.required:
                data.update({"minItems": 1})

        if type_ == "object":
            data.update(
                {
                    "additionalProperties": False,
                    "properties": {},
                    "required": self.yspec["root"].get("required_items", []),
                }
            )
            items = self.yspec["root"]["items"]

            for item_key, item_value in items.items():
                is_invisible = item_key in self.yspec["root"].get("invisible_items", [])
                is_invisible = self.is_invisible if self.is_invisible else is_invisible

                data["properties"][item_key] = self._get_inner(is_invisible=is_invisible, **self.yspec[item_value])

        if not self.required:
            data = {"oneOf": [data, {"type": "null"}]}

        return data


class Group(Field):
    type = "object"

    def __init__(
        self,
        prototype_config: PrototypeConfig,
        object_: ADCMEntity | ConfigHostGroup,
        path_resolver: PathResolver,
        group_fields: QuerySet[PrototypeConfig],
    ):
        super().__init__(prototype_config=prototype_config, object_=object_, path_resolver=path_resolver)
        self.group_fields = group_fields
        self.root_object = object_

    @property
    def activation(self) -> dict | None:
        if "activatable" in self.limits:
            return {"isAllowChange": not self.is_read_only}

        return None

    @property
    def synchronization(self) -> dict | None:
        data = super().synchronization

        if "activatable" not in self.limits:
            return None

        return data

    def get_properties(self) -> dict:
        data = {"properties": OrderedDict(), "required": [], "default": {}}

        for field in self.group_fields:
            data["properties"][field.subname] = get_field(
                prototype_config=field, object_=self.root_object, path_resolver=self._path_resolver
            ).to_dict()
            data["required"].append(field.subname)

        return data

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["additionalProperties"] = False
        data.update(**self.get_properties())

        return data


class List(Field):
    type = "array"

    @property
    def default(self) -> Any:
        default = super().default

        if default is None:
            return []

        return default

    def to_dict(self) -> dict:
        data = super().to_dict()

        data.update(
            {
                "items": {
                    "type": "string",
                    "title": "",
                    "description": "",
                    "default": None,
                    "readOnly": self.is_read_only,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": None,
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                },
            }
        )

        if self.required:
            data.update({"minItems": 1})

        if not self.required:
            return {"oneOf": [data, {"type": "null"}]}

        return data


class Option(Field):
    type = "enum"

    @property
    def enum_extra(self) -> dict | None:
        return {"labels": list(self.limits["option"].keys())}

    def to_dict(self) -> dict:
        data = super().to_dict()

        data.pop("type")
        data.update({"enum": [self.limits["option"][key] for key in self.enum_extra["labels"]]})

        return data


class Variant(Field):
    type = "string"

    def _get_variant(self) -> list | None:
        config: ConfigLog | None = (
            ConfigLog.objects.get(id=self.object_.config.current).config if self.object_.config else None
        )
        values = get_variant(obj=self.object_, conf=config, limits=self.limits)

        if values is None:
            return []

        return values

    @property
    def string_extra(self) -> dict | None:
        string_extra = {"isMultiline": False}

        if not self.limits["source"]["strict"]:
            string_extra.update({"suggestions": self._get_variant()})

        return string_extra

    def to_dict(self) -> dict:
        data = super().to_dict()

        if self.limits["source"]["strict"]:
            data.pop("type")
            data.update({"enum": self._get_variant() or [None]})

            if not self.required and None not in data["enum"]:
                data["enum"].append(None)
        else:
            if self.required:
                data.update({"minLength": 1})
            else:
                data = {"oneOf": [data, {"type": "null"}]}

        return data


def get_field(
    prototype_config: PrototypeConfig,
    object_: ADCMEntity,
    path_resolver: PathResolver,
    group_fields: QuerySet[PrototypeConfig] | None = None,
):
    common_kwargs = {"prototype_config": prototype_config, "object_": object_, "path_resolver": path_resolver}

    match prototype_config.type:
        case "boolean":
            field = Boolean(**common_kwargs)
        case "float":
            field = Float(**common_kwargs)
        case "integer":
            field = Integer(**common_kwargs)
        case "file":
            field = File(**common_kwargs)
        case "json":
            field = Json(**common_kwargs)
        case "password":
            field = Password(**common_kwargs)
        case "secretfile":
            field = SecretFile(**common_kwargs)
        case "secrettext":
            field = SecretText(**common_kwargs)
        case "string":
            field = String(**common_kwargs)
        case "text":
            field = Text(**common_kwargs)
        case "map":
            field = Map(**common_kwargs)
        case "secretmap":
            field = SecretMap(**common_kwargs)
        case "structure":
            field = Structure(**common_kwargs)
        case "group":
            field = Group(**common_kwargs, group_fields=group_fields)
        case "list":
            field = List(**common_kwargs)
        case "option":
            field = Option(**common_kwargs)
        case "variant":
            field = Variant(**common_kwargs)
        case _:
            raise TypeError

    return field


def get_config_schema(
    object_: ADCMEntity | ConfigHostGroup,
    prototype_configs: QuerySet[PrototypeConfig] | list[PrototypeConfig],
    path_resolver: PathResolver,
) -> dict:
    """
    Prepare config schema based on provided `prototype_configs`

    Note that `prototype_configs` entries should be ordered the way you want them to appear in schema's `properties`
    """
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Configuration",
        "description": "",
        "readOnly": False,
        "adcmMeta": {
            "isAdvanced": False,
            "isInvisible": False,
            "activation": None,
            "synchronization": None,
            "nullValue": None,
            "isSecret": False,
            "stringExtra": None,
            "enumExtra": None,
        },
        "type": "object",
        "properties": OrderedDict(),
        "additionalProperties": False,
        "required": [],
    }

    if not prototype_configs:
        return schema

    top_fields = [pc for pc in prototype_configs if pc.subname == ""]

    for field in top_fields:
        if field.type == "group":
            group_fields = [
                pc
                for pc in prototype_configs
                if pc.name == field.name and pc.prototype_id == field.prototype_id and pc.type != "group"
            ]
            item = get_field(
                prototype_config=field, object_=object_, path_resolver=path_resolver, group_fields=group_fields
            ).to_dict()
        else:
            item = get_field(prototype_config=field, object_=object_, path_resolver=path_resolver).to_dict()

        schema["properties"][field.name] = item
        schema["required"].append(field.name)

    return schema


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

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

from typing import Any, Iterable

from cm.models import Action, ADCMEntity, ConcernType, Prototype, PrototypeConfig
from django.http.request import QueryDict
from django_filters import rest_framework as drf_filters
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.serializers import HyperlinkedIdentityField
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST

OBJECT_TYPES_DICT = {
    "adcm": "adcm",
    "cluster": "cluster",
    "service": "service",
    "component": "component",
    "provider": "provider",
    "host provider": "provider",
    "host": "host",
}


def check_obj(model, req, error=None):  # noqa: ARG001
    kwargs = req if isinstance(req, dict) else {"id": req}
    return model.obj.get(**kwargs)


def hlink(view, lookup, lookup_url):
    return HyperlinkedIdentityField(view_name=view, lookup_field=lookup, lookup_url_kwarg=lookup_url)


def save(serializer, code, **kwargs):
    if serializer.is_valid():
        serializer.save(**kwargs)

        return Response(serializer.data, status=code)

    return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


def create(serializer, **kwargs):
    return save(serializer, HTTP_201_CREATED, **kwargs)


def update(serializer, **kwargs):
    return save(serializer, HTTP_200_OK, **kwargs)


def get_api_url_kwargs(obj, request, no_obj_type=False):
    obj_type = obj.prototype.type

    kwargs = {"adcm_pk": obj.pk} if obj_type == "adcm" else {f"{obj_type}_id": obj.id}

    # Do not include object_type in kwargs if no_obj_type == True
    if not no_obj_type:
        kwargs["object_type"] = obj_type

    if obj_type in {"service", "host", "component"} and "cluster" in request.path:
        kwargs["cluster_id"] = obj.cluster.id

    if obj_type == "component" and ("service" in request.path or "cluster" in request.path):
        kwargs["service_id"] = obj.service.id

    return kwargs


def getlist_from_querydict(query_params, field_name):
    params = query_params.get(field_name)
    if params is None:
        return []

    return [param.strip() for param in params.split(",")]


def fix_ordering(field, view):
    fix = field
    if fix != "prototype_id":
        fix = fix.replace("prototype_", "prototype__")

    if fix != "provider_id":
        fix = fix.replace("provider_", "provider__")

    if fix not in ("cluster_id", "cluster_is_null"):
        fix = fix.replace("cluster_", "cluster__")

    if view.__class__.__name__ not in ("BundleList",):
        fix = fix.replace("version", "version_order")

    if view.__class__.__name__ in ["ServiceListView", "ComponentListView"] and "display_name" in fix:
        fix = fix.replace("display_name", "prototype__display_name")

    return fix


class CommonAPIURL(HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, _format):
        kwargs = get_api_url_kwargs(obj, request)

        return reverse(view_name, kwargs=kwargs, request=request, format=_format)


class ObjectURL(HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, _format):
        kwargs = get_api_url_kwargs(obj, request, True)

        return reverse(view_name, kwargs=kwargs, request=request, format=_format)


class UrlField(HyperlinkedIdentityField):
    def get_kwargs(self, obj):  # noqa: ARG002
        return {}

    def get_url(self, obj, view_name, request, _format):  # noqa: ARG002
        kwargs = self.get_kwargs(obj)

        return reverse(self.view_name, kwargs=kwargs, request=request, format=_format)


class AdcmOrderingFilter(OrderingFilter):
    def get_ordering(self, request, queryset, view):
        ordering = None
        fields = getlist_from_querydict(request.query_params, self.ordering_param)
        if fields:
            re_fields = [fix_ordering(field, view) for field in fields]
            ordering = self.remove_invalid_fields(queryset, re_fields, view, request)

        return ordering


class AdcmFilterBackend(drf_filters.DjangoFilterBackend):
    def get_filterset_kwargs(self, request, queryset, view):
        params = request.query_params
        fixed_params = QueryDict(mutable=True)
        for key in params:
            fixed_params[fix_ordering(key, view)] = params[key]

        return {
            "data": fixed_params,
            "queryset": queryset,
            "request": request,
        }


def process_requires(
    proto: Prototype, comp_dict: dict, checked_object: list | None = None, adding_service: bool = False
) -> dict:
    if checked_object is None:
        checked_object = []
    checked_object.append(proto)

    for require in proto.requires:
        req_service = Prototype.obj.get(type="service", name=require["service"], bundle=proto.bundle)

        if req_service.name not in comp_dict:
            comp_dict[req_service.name] = {"components": {}, "service": req_service}

        req_comp = None
        if require.get("component"):
            req_comp = Prototype.obj.get(
                type="component",
                name=require["component"],
                parent=req_service,
            )
            comp_dict[req_service.name]["components"][req_comp.name] = req_comp

        if req_service.requires and req_service not in checked_object:
            process_requires(
                proto=req_service, comp_dict=comp_dict, checked_object=checked_object, adding_service=adding_service
            )

        if req_comp and req_comp.requires and req_comp not in checked_object and not adding_service:
            process_requires(proto=req_comp, comp_dict=comp_dict, checked_object=checked_object)

    return comp_dict


def get_requires(
    prototype: Prototype,
    adding_service: bool = False,
) -> list[dict[str, list[dict[str, Any]] | Any]] | None:
    if not prototype.requires:
        return None

    proto_dict = {}
    proto_dict = process_requires(proto=prototype, comp_dict=proto_dict, adding_service=adding_service)

    out = []

    for service_name, params in proto_dict.items():
        comp_out = []
        service = params["service"]
        for comp_name in params["components"]:
            comp = params["components"][comp_name]
            comp_out.append(
                {
                    "prototype_id": comp.id,
                    "name": comp_name,
                    "display_name": comp.display_name,
                },
            )

        out.append(
            {
                "prototype_id": service.id,
                "name": service_name,
                "display_name": service.display_name,
                "components": comp_out,
            },
        )

    return out


def filter_actions(obj: ADCMEntity, actions: Iterable[Action]):
    """Filter out actions that are not allowed to run on object at that moment"""
    if obj.concerns.filter(type=ConcernType.LOCK).exists():
        return []

    allowed = []
    for action in actions:
        if action.allowed(obj):
            allowed.append(action)
            action.config = PrototypeConfig.objects.filter(prototype=action.prototype, action=action).order_by("id")

    return allowed

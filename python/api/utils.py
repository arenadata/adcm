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

from cm.errors import AdcmEx
from cm.models import Action, ADCMEntity, ConcernType, PrototypeConfig
from django.core.exceptions import ObjectDoesNotExist
from django.http.request import QueryDict
from django_filters import rest_framework as drf_filters
from guardian.shortcuts import get_objects_for_user
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.serializers import HyperlinkedIdentityField
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST


def get_object_for_user(user, perms, klass, **kwargs):
    try:
        queryset = get_objects_for_user(user, perms, klass)

        return queryset.get(**kwargs)
    except ObjectDoesNotExist:
        model = klass
        if not hasattr(klass, "_default_manager"):
            model = klass.model

        error_code = "NO_MODEL_ERROR_CODE"
        if hasattr(model, "__error_code__"):
            error_code = model.__error_code__

        raise AdcmEx(error_code) from None


def check_obj(model, req, error=None):  # pylint: disable=unused-argument
    if isinstance(req, dict):
        kwargs = req
    else:
        kwargs = {"id": req}

    return model.obj.get(**kwargs)


def hlink(view, lookup, lookup_url):
    return HyperlinkedIdentityField(view_name=view, lookup_field=lookup, lookup_url_kwarg=lookup_url)


def check_custom_perm(user, action_type, model, obj, second_perm=None):
    if user.has_perm(f"cm.{action_type}_{model}", obj):
        return

    if second_perm is not None and user.has_perm(f"cm.{second_perm}"):
        return

    raise PermissionDenied()


def save(serializer, code, **kwargs):
    if serializer.is_valid():
        serializer.save(**kwargs)

        return Response(serializer.data, status=code)

    return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


def create(serializer, **kwargs):
    return save(serializer, HTTP_201_CREATED, **kwargs)


def update(serializer, **kwargs):
    return save(serializer, HTTP_200_OK, **kwargs)


def filter_actions(obj: ADCMEntity, actions_set: list[Action]):
    """Filter out actions that are not allowed to run on object at that moment"""
    if obj.concerns.filter(type=ConcernType.LOCK).exists():
        return []

    allowed = []
    for action in actions_set:
        if action.allowed(obj):
            allowed.append(action)
            action.config = PrototypeConfig.objects.filter(prototype=action.prototype, action=action).order_by("id")

    return allowed


def get_api_url_kwargs(obj, request, no_obj_type=False):
    obj_type = obj.prototype.type

    if obj_type == "adcm":
        kwargs = {"adcm_pk": obj.pk}
    else:
        kwargs = {f"{obj_type}_id": obj.id}

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

    if view.__class__.__name__ in ["ServiceListView", "ComponentListView"]:
        if "display_name" in fix:
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
    def get_kwargs(self, obj):  # pylint: disable=unused-argument
        return {}

    def get_url(self, obj, view_name, request, _format):
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


class SuperuserOnlyMixin:
    not_superuser_error_code = None

    def get_queryset(self, *args, **kwargs):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.model.objects.none()

        if not self.request.user.is_superuser:
            if self.not_superuser_error_code:
                raise AdcmEx(self.not_superuser_error_code)

            return self.queryset.model.objects.none()

        return super().get_queryset(*args, **kwargs)

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

# pylint: disable=not-callable, unused-import, too-many-locals

import rest_framework.pagination
from django.conf import settings
from django.core.exceptions import FieldError, ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import SAFE_METHODS, DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.viewsets import ViewSetMixin

from adcm.permissions import DjangoObjectPermissionsAudit
from api.utils import AdcmFilterBackend, AdcmOrderingFilter, getlist_from_querydict
from audit.utils import audit
from cm.errors import AdcmEx


class ModelPermOrReadOnlyForAuth(DjangoModelPermissions):
    @audit
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.method in SAFE_METHODS:
                return True
            else:
                queryset = self._queryset(view)
                perms = self.get_required_permissions(request.method, queryset.model)

                return request.user.has_perms(perms)

        return False


class GenericUIView(GenericAPIView):
    """
    GenericAPIView with extended selection for serializer class
    (switched by query parameter view=interface)
    """

    permission_classes = (DjangoObjectPermissionsAudit,)
    serializer_class_post: serializers.Serializer = None
    serializer_class_put: serializers.Serializer = None
    serializer_class_patch: serializers.Serializer = None
    serializer_class_ui: serializers.Serializer = None
    serializer_class: serializers.Serializer = None

    def _is_for_ui(self) -> bool:
        if not self.request:
            return False
        view = self.request.query_params.get("view", None)
        return view == "interface"

    def get_serializer_class(self):
        if self.request is not None:
            if self.request.method == "POST":
                if self.serializer_class_post:
                    return self.serializer_class_post
            elif self.request.method == "PUT":
                if self.serializer_class_put:
                    return self.serializer_class_put
            elif self.request.method == "PATCH":
                if self.serializer_class_patch:
                    return self.serializer_class_patch
            elif self._is_for_ui():
                if self.serializer_class_ui:
                    return self.serializer_class_ui

        return super().get_serializer_class()


class GenericUIViewSet(ViewSetMixin, GenericAPIView):
    def is_for_ui(self) -> bool:
        if not self.request:
            return False

        view = self.request.query_params.get("view")

        return view == "interface"


class PaginatedView(GenericUIView):
    """
    GenericAPIView with pagination
    extended with selection of serializer class
    """

    filter_backends = (AdcmFilterBackend, AdcmOrderingFilter)
    pagination_class = rest_framework.pagination.LimitOffsetPagination

    @staticmethod
    def get_ordering(request, queryset, view):
        return AdcmOrderingFilter().get_ordering(request, queryset, view)

    def is_paged(self, request):
        limit = self.request.query_params.get("limit", False)
        offset = self.request.query_params.get("offset", False)

        return bool(limit or offset)

    def get_paged_link(self):
        page = self.paginator
        url = self.request.build_absolute_uri()
        url = replace_query_param(url, page.limit_query_param, page.limit)
        url = replace_query_param(url, page.offset_query_param, 0)

        return url

    def get_page(self, obj, request, context=None):
        if not context:
            context = {}

        context["request"] = request
        count = obj.count()
        serializer_class = self.get_serializer_class()

        if "fields" in request.query_params or "distinct" in request.query_params:
            serializer_class = None
            try:
                fields = getlist_from_querydict(request.query_params, "fields")
                distinct = int(request.query_params.get("distinct", 0))

                if fields and distinct:
                    obj = obj.values(*fields).distinct()
                elif fields:
                    obj = obj.values(*fields)

            except (FieldError, ValueError):
                query_params = ",".join(
                    [f"{k}={v}" for k, v in request.query_params.items() if k in ["fields", "distinct"]]
                )
                msg = f"Bad query params: {query_params}"

                raise AdcmEx("BAD_QUERY_PARAMS", msg=msg) from None

        page = self.paginate_queryset(obj)
        if self.is_paged(request):
            if serializer_class is not None:
                serializer = serializer_class(page, many=True, context=context)
                page = serializer.data

            return self.get_paginated_response(page)

        if count <= settings.REST_FRAMEWORK["PAGE_SIZE"]:
            if serializer_class is not None:
                serializer = serializer_class(obj, many=True, context=context)
                obj = serializer.data

            return Response(obj)

        msg = "Response is too long, use paginated request"

        raise AdcmEx("TOO_LONG", msg=msg, args=self.get_paged_link())

    def get(self, request, *args, **kwargs):
        obj = self.filter_queryset(self.get_queryset())

        return self.get_page(obj, request)


class DetailView(GenericUIView):
    """
    GenericAPIView for single object
    extended with selection of serializer class
    """

    error_code = "OBJECT_NOT_FOUND"

    def check_obj(self, kw_req):
        try:
            return self.get_queryset().get(**kw_req)
        except ObjectDoesNotExist:
            raise AdcmEx(self.error_code) from None

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        kw_req = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = self.check_obj(kw_req)
        self.check_object_permissions(self.request, obj)

        return obj

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj)

        return Response(serializer.data)

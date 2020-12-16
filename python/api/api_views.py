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

from django.core.exceptions import ObjectDoesNotExist, FieldError
from django.http.request import QueryDict
from django_filters import rest_framework as drf_filters

import rest_framework.pagination
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.utils.urls import replace_query_param
from rest_framework.permissions import DjangoModelPermissions

from adcm.settings import REST_FRAMEWORK

from cm.models import Action
from cm.errors import AdcmApiEx
from cm.logger import log


def check_obj(model, kw_req, error):
    try:
        return model.get(**kw_req)
    except ObjectDoesNotExist:
        raise AdcmApiEx(error) from None


def save(serializer, code, **kwargs):
    if serializer.is_valid():
        serializer.save(**kwargs)
        return Response(serializer.data, status=code)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def create(serializer, **kwargs):
    return save(serializer, status.HTTP_201_CREATED, **kwargs)


def update(serializer, **kwargs):
    return save(serializer, status.HTTP_200_OK, **kwargs)


class DjangoModelPerm(DjangoModelPermissions):
    """
    Similar to `DjangoModelPermissions`, but adding 'view' permissions.
    """
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


class GenericAPIPermView(GenericAPIView):
    permission_classes = (DjangoModelPerm,)


class InterfaceView():
    def for_ui(self, request):
        view = self.request.query_params.get('view', None)
        return bool(view == 'interface')

    def select_serializer(self, request):
        """
        That is special function to handle api calls from UI.

        UI send special GET parameter view=interface to switch between
        regular and extended serializer
        """
        if request.method == 'POST':
            if hasattr(self, 'serializer_class_post'):
                return self.serializer_class_post
        elif self.for_ui(request):
            if hasattr(self, 'serializer_class_ui'):
                return self.serializer_class_ui
        return self.serializer_class


def getlist_from_querydict(query_params, field_name):
    params = query_params.get(field_name)
    if params is None:
        return []
    return [param.strip() for param in params.split(',')]


def fix_ordering(field, view):
    fix = field
    if fix != 'prototype_id':
        fix = fix.replace('prototype_', 'prototype__')
    if fix != 'provider_id':
        fix = fix.replace('provider_', 'provider__')
    if fix not in ('cluster_id', 'cluster_is_null'):
        fix = fix.replace('cluster_', 'cluster__')
    if view.__class__.__name__ not in ('BundleList',):
        fix = fix.replace('version', 'version_order')
    if view.__class__.__name__ == 'ClusterServiceList':
        if 'display_name' in fix:
            fix = fix.replace('display_name', 'prototype__display_name')
    elif view.__class__.__name__ == 'ServiceComponentList':
        if 'display_name' in fix:
            fix = fix.replace('display_name', 'component__display_name')
    return fix


class ActionFilter(drf_filters.FilterSet):
    button_is_null = drf_filters.BooleanFilter(field_name='button', lookup_expr='isnull')

    class Meta:
        model = Action
        fields = ('name', 'button')


class AdcmOrderingFilter(OrderingFilter):
    def get_ordering(self, request, queryset, view):
        ordering = None
        fields = getlist_from_querydict(request.query_params, self.ordering_param)
        if fields:
            re_fields = [fix_ordering(field, view) for field in fields]
            ordering = self.remove_invalid_fields(queryset, re_fields, view, request)
        # log.debug('ordering: %s', ordering)
        return ordering


class AdcmFilterBackend(drf_filters.DjangoFilterBackend):
    def get_filterset_kwargs(self, request, queryset, view):
        params = request.query_params
        fixed_params = QueryDict(mutable=True)
        for key in params:
            fixed_params[fix_ordering(key, view)] = params[key]
        # log.debug('filtering: %s before: %s, after: %s', view, params, fixed_params)
        return {
            'data': fixed_params,
            'queryset': queryset,
            'request': request,
        }


class PageView(GenericAPIView, InterfaceView):
    filter_backends = (AdcmFilterBackend, AdcmOrderingFilter)
    pagination_class = rest_framework.pagination.LimitOffsetPagination
    permission_classes = (DjangoModelPerm,)

    def get_ordering(self, request, queryset, view):
        Order = AdcmOrderingFilter()
        return Order.get_ordering(request, queryset, view)

    def is_paged(self, request):
        limit = self.request.query_params.get('limit', False)
        offset = self.request.query_params.get('offset', False)
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
        context['request'] = request
        count = obj.count()
        serializer_class = self.select_serializer(request)

        if 'fields' in request.query_params or 'distinct' in request.query_params:
            serializer_class = None
            try:
                fields = getlist_from_querydict(request.query_params, 'fields')
                distinct = int(request.query_params.get('distinct', 0))

                if fields and distinct:
                    obj = obj.values(*fields).distinct()
                elif fields:
                    obj = obj.values(*fields)

            except (FieldError, ValueError):
                qp = ','.join([f'{k}={v}' for k, v in request.query_params.items()
                               if k in ['fields', 'distinct']])
                msg = f'Bad query params: {qp}'
                raise AdcmApiEx('BAD_QUERY_PARAMS', msg=msg) from None

        page = self.paginate_queryset(obj)
        if self.is_paged(request):
            if serializer_class is not None:
                serializer = serializer_class(page, many=True, context=context)
                page = serializer.data
            return self.get_paginated_response(page)

        if count <= REST_FRAMEWORK['PAGE_SIZE']:
            if serializer_class is not None:
                serializer = serializer_class(obj, many=True, context=context)
                obj = serializer.data
            return Response(obj)

        msg = 'Response is too long, use paginated request'
        raise AdcmApiEx('TOO_LONG', msg=msg, args=self.get_paged_link())

    def get(self, request):
        obj = self.filter_queryset(self.get_queryset())
        return self.get_page(obj, request)


class PageViewAdd(PageView):
    def post(self, request):
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(data=request.data, context={'request': request})
        return create(serializer)


class ListView(GenericAPIView, InterfaceView):
    filter_backends = (AdcmFilterBackend,)
    permission_classes = (DjangoModelPerm,)

    def get(self, request, *args, **kwargs):
        obj = self.filter_queryset(self.get_queryset())
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(obj, many=True, context={'request': request})
        return Response(serializer.data)


class ListViewAdd(ListView):
    def post(self, request):
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(data=request.data, context={'request': request})
        return create(serializer)


class DetailViewRO(GenericAPIView, InterfaceView):
    permission_classes = (DjangoModelPerm,)

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        kw_req = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        return check_obj(self.get_queryset(), kw_req, self.error_code)

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(obj, context={'request': request})
        return Response(serializer.data)


class DetailViewEdit(DetailViewRO):
    def put(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.serializer_class(obj, data=request.data, context={'request': request})
        return update(serializer)


class DetailViewDelete(DetailViewRO):
    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

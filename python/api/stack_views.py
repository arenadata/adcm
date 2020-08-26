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

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.authentication import TokenAuthentication, SessionAuthentication

import cm.api
import cm.bundle
from cm.errors import AdcmEx, AdcmApiEx
from cm.models import Bundle, Prototype, Component, Action
from cm.models import PrototypeConfig, Upgrade, PrototypeExport
from cm.models import PrototypeImport
from cm.logger import log   # pylint: disable=unused-import

import api.serializers
import api.stack_serial
from api.serializers import check_obj
from api.api_views import ListView, DetailViewRO, PageView, GenericAPIPermView


class CsrfOffSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  #


class Stack(GenericAPIPermView):
    queryset = Prototype.objects.all()
    serializer_class = api.stack_serial.Stack

    def get(self, request):
        """
        Operations with stack of services
        """
        obj = Bundle()
        serializer = self.serializer_class(obj, context={'request': request})
        return Response(serializer.data)


class UploadBundle(GenericAPIPermView):
    queryset = Bundle.objects.all()
    serializer_class = api.stack_serial.UploadBundle
    authentication_classes = (CsrfOffSessionAuthentication, TokenAuthentication)
    parser_classes = (MultiPartParser,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoadBundle(GenericAPIPermView):
    queryset = Prototype.objects.all()
    serializer_class = api.stack_serial.LoadBundle

    def post(self, request):
        """
        post:
        Load bundle
        """
        try:
            serializer = self.serializer_class(data=request.data, context={'request': request})
            if serializer.is_valid():
                bundle = cm.bundle.load_bundle(serializer.validated_data.get('bundle_file'))
                srl = api.stack_serial.BundleSerializer(bundle, context={'request': request})
                return Response(srl.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e


class BundleList(PageView):
    """
    get:
    List all bundles
    """
    queryset = Bundle.objects.exclude(hash='adcm')
    serializer_class = api.stack_serial.BundleSerializer
    filterset_fields = ('name', 'version')
    ordering_fields = ('name', 'version_order')


class BundleDetail(DetailViewRO):
    """
    get:
    Show bundle

    delete:
    Remove bundle
    """
    queryset = Bundle.objects.all()
    serializer_class = api.stack_serial.BundleSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'bundle_id'
    error_code = 'BUNDLE_NOT_FOUND'

    def delete(self, request, bundle_id):
        bundle = check_obj(Bundle, bundle_id, 'BUNDLE_NOT_FOUND')
        try:
            cm.bundle.delete_bundle(bundle)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e
        return Response(status=status.HTTP_204_NO_CONTENT)


class BundleUpdate(GenericAPIPermView):
    queryset = Bundle.objects.all()
    serializer_class = api.stack_serial.BundleSerializer

    def put(self, request, bundle_id):
        """
        update bundle
        """
        bundle = check_obj(Bundle, bundle_id, 'BUNDLE_NOT_FOUND')
        try:
            cm.bundle.update_bundle(bundle)
            serializer = self.serializer_class(bundle, context={'request': request})
            return Response(serializer.data)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code, e.adds) from e


class BundleLicense(GenericAPIPermView):
    action = 'retrieve'
    queryset = Bundle.objects.all()
    serializer_class = api.stack_serial.LicenseSerializer

    def get(self, request, bundle_id):
        bundle = check_obj(Bundle, bundle_id, 'BUNDLE_NOT_FOUND')
        try:
            body = cm.api.get_license(bundle)
            url = reverse('accept-license', kwargs={'bundle_id': bundle.id}, request=request)
            return Response({'license': bundle.license, 'accept': url, 'text': body})
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code, e.adds) from e


class AcceptLicense(GenericAPIPermView):
    queryset = Bundle.objects.all()
    serializer_class = api.stack_serial.LicenseSerializer

    def put(self, request, bundle_id):
        bundle = check_obj(Bundle, bundle_id, 'BUNDLE_NOT_FOUND')
        try:
            cm.api.accept_license(bundle)
            return Response(status=status.HTTP_200_OK)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code, e.adds) from e


class PrototypeList(PageView):
    """
    get:
    List all stack prototypes
    """
    queryset = Prototype.objects.all()
    serializer_class = api.stack_serial.PrototypeSerializer
    filterset_fields = ('name', 'bundle_id', 'type')
    ordering_fields = ('display_name', 'version_order')


class ServiceList(PageView):
    """
    get:
    List all stack services
    """
    queryset = Prototype.objects.filter(type='service')
    serializer_class = api.stack_serial.ServiceSerializer
    filterset_fields = ('name', 'bundle_id')
    ordering_fields = ('display_name', 'version_order')


class ServiceDetail(DetailViewRO):
    """
    get:
    Show stack service
    """
    queryset = Prototype.objects.filter(type='service')
    serializer_class = api.stack_serial.ServiceDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'prototype_id'
    error_code = 'SERVICE_NOT_FOUND'

    def get_object(self):
        service = super().get_object()
        service.actions = Action.objects.filter(prototype__type='service', prototype__id=service.id)
        service.components = Component.objects.filter(prototype=service)
        service.config = PrototypeConfig.objects.filter(
            prototype=service, action=None
        ).order_by('id')
        service.exports = PrototypeExport.objects.filter(prototype=service)
        service.imports = PrototypeImport.objects.filter(prototype=service)
        return service


class ProtoActionDetail(GenericAPIPermView):
    queryset = Action.objects.all()
    serializer_class = api.serializers.ActionSerializer

    def get(self, request, action_id):
        """
        Show action
        """
        obj = check_obj(Action, action_id, 'ACTION_NOT_FOUND')
        serializer = self.serializer_class(obj, context={'request': request})
        return Response(serializer.data)


class ServiceProtoActionList(GenericAPIPermView):
    queryset = Action.objects.filter(prototype__type='service')
    serializer_class = api.serializers.ActionSerializer

    def get(self, request, service_id):
        """
        List all actions of a specified service
        """
        obj = self.get_queryset().filter(prototype_id=service_id)
        serializer = self.serializer_class(obj, many=True, context={'request': request})
        return Response(serializer.data)


class HostTypeList(PageView):
    """
    get:
    List all host types
    """
    queryset = Prototype.objects.filter(type='host')
    serializer_class = api.stack_serial.HostTypeSerializer
    filterset_fields = ('name', 'bundle_id')
    ordering_fields = ('display_name', 'version_order')


class ProviderTypeList(PageView):
    """
    get:
    List all host providers types
    """
    queryset = Prototype.objects.filter(type='provider')
    serializer_class = api.stack_serial.ProviderTypeSerializer
    filterset_fields = ('name', 'bundle_id', 'display_name')
    ordering_fields = ('display_name', 'version_order')


class ClusterTypeList(PageView):
    """
    get:
    List all cluster types
    """
    queryset = Prototype.objects.filter(type='cluster')
    serializer_class = api.stack_serial.ClusterTypeSerializer
    filterset_fields = ('name', 'bundle_id', 'display_name')
    ordering_fields = ('display_name', 'version_order')


class AdcmTypeList(ListView):
    """
    get:
    List adcm root object prototypes
    """
    queryset = Prototype.objects.filter(type='adcm')
    serializer_class = api.stack_serial.AdcmTypeSerializer
    filterset_fields = ('bundle_id',)


class PrototypeDetail(DetailViewRO):
    """
    get:
    Show prototype
    """
    queryset = Prototype.objects.all()
    serializer_class = api.stack_serial.PrototypeDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'prototype_id'
    error_code = 'PROTOTYPE_NOT_FOUND'

    def get_object(self):
        obj_type = super().get_object()
        act_set = []
        for action in Action.objects.filter(prototype__id=obj_type.id):
            action.config = PrototypeConfig.objects.filter(prototype__id=obj_type.id, action=action)
            act_set.append(action)
        obj_type.actions = act_set
        obj_type.config = PrototypeConfig.objects.filter(prototype=obj_type, action=None)
        obj_type.imports = PrototypeImport.objects.filter(prototype=obj_type)
        obj_type.exports = PrototypeExport.objects.filter(prototype=obj_type)
        obj_type.upgrade = Upgrade.objects.filter(bundle=obj_type.bundle)
        return obj_type


class AdcmTypeDetail(PrototypeDetail):
    """
    get:
    Show adcm prototype
    """
    queryset = Prototype.objects.filter(type='adcm')
    serializer_class = api.stack_serial.AdcmTypeDetailSerializer


class ClusterTypeDetail(PrototypeDetail):
    """
    get:
    Show cluster prototype
    """
    queryset = Prototype.objects.filter(type='cluster')
    serializer_class = api.stack_serial.ClusterTypeDetailSerializer


class HostTypeDetail(PrototypeDetail):
    """
    get:
    Show host prototype
    """
    queryset = Prototype.objects.filter(type='host')
    serializer_class = api.stack_serial.HostTypeDetailSerializer


class ProviderTypeDetail(PrototypeDetail):
    """
    get:
    Show host provider prototype
    """
    queryset = Prototype.objects.filter(type='provider')
    serializer_class = api.stack_serial.ProviderTypeDetailSerializer


class LoadServiceMap(GenericAPIPermView):
    queryset = Prototype.objects.all()
    serializer_class = api.stack_serial.Stack

    def put(self, request):
        cm.status_api.load_service_map()
        return Response(status=status.HTTP_200_OK)

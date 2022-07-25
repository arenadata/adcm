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

from django.urls import include, path

from api.stack import root, views

PROTOTYPE_ID = '<int:prototype_id>/'


# fmt: off
urlpatterns = [
    path('', root.StackRoot.as_view(), name='stack'),
    path('upload/', views.UploadBundle.as_view(), name='upload-bundle'),
    path('load/', views.LoadBundle.as_view({'post': 'create'}), name='load-bundle'),
    path(
        'load/servicemap/', views.LoadBundle.as_view({'put': 'servicemap'}), name='load-servicemap'
    ),
    path(
        'load/hostmap/', views.LoadBundle.as_view({'put': 'hostmap'}), name='load-hostmap'
    ),
    path('bundle/', include([
        path('', views.BundleList.as_view(), name='bundle'),
        path('<int:bundle_id>/', include([
            path('', views.BundleDetail.as_view(), name='bundle-details'),
            path('update/', views.BundleUpdate.as_view(), name='bundle-update'),
            path('license/', views.BundleLicense.as_view(), name='bundle-license'),
            path('license/accept/', views.AcceptLicense.as_view(), name='accept-license'),
        ])),
    ])),
    path('action/<int:action_id>/', views.ProtoActionDetail.as_view(), name='action-details'),
    path('prototype/', include([
        path('', views.PrototypeList.as_view(), name='prototype'),
        path(PROTOTYPE_ID, views.PrototypeDetail.as_view(), name='prototype-details')
    ])),
    path('service/', include([
        path('', views.ServiceList.as_view(), name='service-type'),
        path(PROTOTYPE_ID, include([
            path('', views.ServiceDetail.as_view(), name='service-type-details'),
            path('action/', views.ServiceProtoActionList.as_view(), name='service-actions'),
        ])),
    ])),
    path('component/', include([
        path('', views.ComponentList.as_view(), name='component-type'),
        path(PROTOTYPE_ID, views.ComponentTypeDetail.as_view(), name='component-type-details'),
    ])),
    path('provider/', include([
        path('', views.ProviderTypeList.as_view(), name='provider-type'),
        path(PROTOTYPE_ID, views.ProviderTypeDetail.as_view(), name='provider-type-details'),
    ])),
    path('host/', include([
        path('', views.HostTypeList.as_view(), name='host-type'),
        path(PROTOTYPE_ID, views.HostTypeDetail.as_view(), name='host-type-details'),
    ])),
    path('cluster/', include([
        path('', views.ClusterTypeList.as_view(), name='cluster-type'),
        path(PROTOTYPE_ID, views.ClusterTypeDetail.as_view(), name='cluster-type-details'),
    ])),
    path('adcm/', include([
        path('', views.AdcmTypeList.as_view(), name='adcm-type'),
        path(PROTOTYPE_ID, views.AdcmTypeDetail.as_view(), name='adcm-type-details'),
    ])),
]
# fmt: on

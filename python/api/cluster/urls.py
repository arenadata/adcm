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

from api.cluster import views

# fmt: off
urlpatterns = [
    path('', views.ClusterList.as_view(), name='cluster'),
    path('<int:cluster_id>/', include([
        path('', views.ClusterDetail.as_view(), name='cluster-details'),
        path('import/', views.ClusterImport.as_view(), name='cluster-import'),
        path('status/', views.StatusList.as_view(), name='cluster-status'),
        path('serviceprototype/', views.ClusterBundle.as_view(), name='cluster-service-prototype'),
        path('service/', include('api.service.urls')),
        path('host/', include('api.host.cluster_urls')),
        path('action/', include('api.action.urls'), {'object_type': 'cluster'}),
        path('config/', include('api.config.urls'), {'object_type': 'cluster'}),
        path('bind/', include([
            path('', views.ClusterBindList.as_view(), name='cluster-bind'),
            path('<int:bind_id>/', views.ClusterBindDetail.as_view(), name='cluster-bind-details'),
        ])),
        path('upgrade/', include([
            path('', views.ClusterUpgrade.as_view(), name='cluster-upgrade'),
            path('<int:upgrade_id>/', include([
                path('', views.ClusterUpgradeDetail.as_view(), name='cluster-upgrade-details'),
                path('do/', views.DoClusterUpgrade.as_view(), name='do-cluster-upgrade'),
            ])),
        ])),
        path('hostcomponent/', include([
            path('', views.HostComponentList.as_view(), name='host-component'),
            path('<int:hs_id>/', views.HostComponentDetail.as_view(), name='host-comp-details'),
        ])),
    ])),
]
# fmt: on

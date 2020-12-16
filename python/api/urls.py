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

from django.urls import path, register_converter
from django.conf.urls import include

from rest_framework_swagger.views import get_swagger_view
from rest_framework.schemas import get_schema_view

from api import views, user_views, stack_views, cluster_views, docs, job_views


register_converter(views.NameConverter, 'name')
swagger_view = get_swagger_view(title='ArenaData Chapel API')
schema_view = get_schema_view(title='ArenaData Chapel API')


CLUSTER = 'cluster/<int:cluster_id>/'
PROVIDER = 'provider/<int:provider_id>/'
HOST = 'host/<int:host_id>/'
SERVICE = 'service/<int:service_id>/'
SERVICE_CONFIG = CLUSTER + SERVICE + 'config/'


urlpatterns = [
    path('info/', views.ADCMInfo.as_view(), name='adcm-info'),
    path('token/', views.GetAuthToken.as_view(), name='token'),
    path('logout/', views.LogOut.as_view(), name='logout'),

    path('user/', user_views.UserList.as_view(), name='user-list'),
    path('user/<name:username>/', user_views.UserDetail.as_view(), name='user-details'),
    path(
        'user/<name:username>/role/', user_views.ChangeUserRole.as_view(), name='change-user-role'
    ),
    path('user/<name:username>/group/', user_views.AddUser2Group.as_view(), name='add-user-group'),
    path('user/<name:username>/password/', user_views.UserPasswd.as_view(), name='user-passwd'),

    path('group/', user_views.GroupList.as_view(), name='group-list'),
    path('group/<name:name>/', user_views.GroupDetail.as_view(), name='group-details'),
    path('group/<name:name>/role/', user_views.ChangeGroupRole.as_view(), name='change-group-role'),

    path('profile/', user_views.ProfileList.as_view(), name='profile-list'),
    path('profile/<name:username>/', user_views.ProfileDetail.as_view(), name='profile-details'),
    path(
        'profile/<name:username>/password/', user_views.UserPasswd.as_view(), name='profile-passwd'
    ),

    path('role/', user_views.RoleList.as_view(), name='role-list'),
    path('role/<int:role_id>/', user_views.RoleDetail.as_view(), name='role-details'),

    path('stats/', views.Stats.as_view(), name='stats'),
    path('stats/task/<int:task_id>/', views.TaskStats.as_view(), name='task-stats'),
    path('stats/job/<int:job_id>/', views.JobStats.as_view(), name='job-stats'),

    path('stack/', stack_views.Stack.as_view(), name='stack'),
    path('stack/upload/', stack_views.UploadBundle.as_view(), name='upload-bundle'),
    path('stack/load/', stack_views.LoadBundle.as_view(), name='load-bundle'),
    path(
        'stack/load/servicemap/',
        stack_views.LoadServiceMap.as_view(),
        name='load-servicemap'
    ),
    path('stack/bundle/', stack_views.BundleList.as_view(), name='bundle'),
    path(
        'stack/bundle/<int:bundle_id>/',
        stack_views.BundleDetail.as_view(),
        name='bundle-details'
    ),
    path(
        'stack/bundle/<int:bundle_id>/update/',
        stack_views.BundleUpdate.as_view(),
        name='bundle-update'
    ),
    path(
        'stack/bundle/<int:bundle_id>/license/',
        stack_views.BundleLicense.as_view(),
        name='bundle-license'
    ),
    path(
        'stack/bundle/<int:bundle_id>/license/accept/',
        stack_views.AcceptLicense.as_view(),
        name='accept-license'
    ),
    path(
        'stack/action/<int:action_id>/',
        stack_views.ProtoActionDetail.as_view(),
        name='action-details'
    ),
    path('stack/prototype/', stack_views.PrototypeList.as_view(), name='prototype'),
    path('stack/service/', stack_views.ServiceList.as_view(), name='service-type'),
    path(
        'stack/service/<int:prototype_id>/',
        stack_views.ServiceDetail.as_view(),
        name='service-type-details'
    ),
    path(
        'stack/' + SERVICE + 'action/',
        stack_views.ServiceProtoActionList.as_view(),
        name='service-actions'
    ),
    path('stack/provider/', stack_views.ProviderTypeList.as_view(), name='provider-type'),
    path(
        'stack/provider/<int:prototype_id>/',
        stack_views.ProviderTypeDetail.as_view(),
        name='provider-type-details'
    ),
    path('stack/host/', stack_views.HostTypeList.as_view(), name='host-type'),
    path(
        'stack/host/<int:prototype_id>/',
        stack_views.HostTypeDetail.as_view(),
        name='host-type-details'
    ),
    path('stack/cluster/', stack_views.ClusterTypeList.as_view(), name='cluster-type'),
    path(
        'stack/cluster/<int:prototype_id>/',
        stack_views.ClusterTypeDetail.as_view(),
        name='cluster-type-details'
    ),
    path('stack/adcm/', stack_views.AdcmTypeList.as_view(), name='adcm-type'),
    path(
        'stack/adcm/<int:prototype_id>/',
        stack_views.AdcmTypeDetail.as_view(),
        name='adcm-type-details'
    ),
    path(
        'stack/prototype/<int:prototype_id>/',
        stack_views.PrototypeDetail.as_view(),
        name='prototype-details'
    ),

    path('cluster/', cluster_views.ClusterList.as_view(), name='cluster'),
    path(CLUSTER, cluster_views.ClusterDetail.as_view(), name='cluster-details'),
    path(CLUSTER + 'action/', cluster_views.ClusterActionList.as_view(), name='cluster-action'),
    path(CLUSTER + 'host/', cluster_views.ClusterHostList.as_view(), name='cluster-host'),
    path(CLUSTER + 'import/', cluster_views.ClusterImport.as_view(), name='cluster-import'),
    path(CLUSTER + 'upgrade/', cluster_views.ClusterUpgrade.as_view(), name='cluster-upgrade'),
    path(CLUSTER + 'bind/', cluster_views.ClusterBindList.as_view(), name='cluster-bind'),
    path(
        CLUSTER + 'bind/<int:bind_id>/',
        cluster_views.ClusterServiceBindDetail.as_view(),
        name='cluster-bind-details'
    ),
    path(
        CLUSTER + 'serviceprototype/',
        cluster_views.ClusterBundle.as_view(),
        name='cluster-service-prototype'
    ),
    path(
        CLUSTER + 'upgrade/<int:upgrade_id>/',
        cluster_views.ClusterUpgradeDetail.as_view(),
        name='cluster-upgrade-details'
    ),
    path(
        CLUSTER + 'upgrade/<int:upgrade_id>/do/',
        cluster_views.DoClusterUpgrade.as_view(),
        name='do-cluster-upgrade'
    ),
    path(
        CLUSTER + HOST, cluster_views.ClusterHostDetail.as_view(), name='cluster-host-details'
    ),
    path(
        CLUSTER + 'service/', cluster_views.ClusterServiceList.as_view(), name='cluster-service'
    ),
    path(
        CLUSTER + HOST + 'action/',
        cluster_views.ClusterHostActionList.as_view(),
        name='cluster-host-action'
    ),
    path(
        CLUSTER + HOST + 'action/<int:action_id>/',
        cluster_views.ClusterHostAction.as_view(),
        name='cluster-host-action-details'
    ),
    path(
        CLUSTER + HOST + 'action/<int:action_id>/run/',
        cluster_views.ClusterHostTask.as_view(),
        name='cluster-host-action-run'
    ),
    path(
        CLUSTER + 'action/<int:action_id>/',
        cluster_views.ClusterAction.as_view(),
        name='cluster-action-details'
    ),
    path(
        CLUSTER + 'action/<int:action_id>/run/',
        cluster_views.ClusterTask.as_view(),
        name='cluster-action-run'
    ),
    path(
        CLUSTER + 'status/',
        cluster_views.StatusList.as_view(),
        name='cluster-status'
    ),
    path(
        CLUSTER + 'hostcomponent/',
        cluster_views.HostComponentList.as_view(),
        name='host-component'
    ),
    path(
        CLUSTER + 'hostcomponent/<int:hs_id>/',
        cluster_views.HostComponentDetail.as_view(),
        name='host-component-details'
    ),
    path(
        CLUSTER + SERVICE,
        cluster_views.ClusterServiceDetail.as_view(),
        name='cluster-service-details'
    ),
    path(
        CLUSTER + SERVICE + 'action/',
        cluster_views.ClusterServiceActionList.as_view(),
        name='cluster-service-action'
    ),
    path(
        CLUSTER + SERVICE + 'action/<int:action_id>/',
        cluster_views.ClusterServiceAction.as_view(),
        name='cluster-service-action-details'
    ),
    path(
        CLUSTER + SERVICE + 'action/<int:action_id>/run/',
        cluster_views.ClusterServiceTask.as_view(),
        name='cluster-service-action-run'
    ),
    path(
        CLUSTER + SERVICE + 'component/',
        cluster_views.ServiceComponentList.as_view(),
        name='cluster-service-component'
    ),
    path(
        CLUSTER + SERVICE + 'component/<int:component_id>/',
        cluster_views.ServiceComponentDetail.as_view(),
        name='cluster-service-component-details'
    ),
    path(
        CLUSTER + SERVICE + 'import/',
        cluster_views.ClusterServiceImport.as_view(),
        name='cluster-service-import'
    ),
    path(
        CLUSTER + SERVICE + 'bind/',
        cluster_views.ClusterServiceBind.as_view(),
        name='cluster-service-bind'
    ),
    path(
        CLUSTER + SERVICE + 'bind/<int:bind_id>/',
        cluster_views.ClusterServiceBindDetail.as_view(),
        name='cluster-service-bind-details'
    ),
    path(CLUSTER + 'config/', include('api.config.urls'), {'object_type': 'cluster'}),

    path(
        SERVICE_CONFIG,
        cluster_views.ClusterServiceConfig.as_view(),
        name='cluster-service-config'
    ),
    path(
        SERVICE_CONFIG + 'previous/',
        cluster_views.ClusterServiceConfigVersion.as_view(),
        {'version': 'previous'},
        name='cluster-service-config-prev'
    ),
    path(
        SERVICE_CONFIG + 'current/',
        cluster_views.ClusterServiceConfigVersion.as_view(),
        {'version': 'current'},
        name='cluster-service-config-curr'
    ),
    path(
        SERVICE_CONFIG + 'history/<int:version>/',
        cluster_views.ClusterServiceConfigVersion.as_view(),
        name='cluster-service-config-id'
    ),
    path(
        SERVICE_CONFIG + 'history/<int:version>/restore/',
        cluster_views.ClusterConfigRestore.as_view(),
        name='cluster-service-config-restore'
    ),
    path(
        SERVICE_CONFIG + 'history/',
        cluster_views.ClusterServiceConfigHistory.as_view(),
        name='cluster-service-config-history'
    ),
    path('service/', include('api.service.urls')),

    path('adcm/', views.AdcmList.as_view(), name='adcm'),
    path('adcm/<int:adcm_id>/', views.AdcmDetail.as_view(), name='adcm-details'),
    path('adcm/<int:adcm_id>/config/', include('api.config.urls'), {'object_type': 'adcm'}),
    path('adcm/<int:adcm_id>/action/', views.ADCMActionList.as_view(), name='adcm-action'),
    path(
        'adcm/<int:adcm_id>/action/<int:action_id>/',
        views.ADCMAction.as_view(),
        name='adcm-action-details'
    ),
    path(
        'adcm/<int:adcm_id>/action/<int:action_id>/run/',
        views.ADCMTask.as_view(),
        name='adcm-action-run'
    ),
    path('provider/', views.ProviderList.as_view(), name='provider'),
    path(PROVIDER, views.ProviderDetail.as_view(), name='provider-details'),
    path(PROVIDER + 'host/', views.ProviderHostList.as_view(), name='provider-host'),

    path(PROVIDER + 'action/', views.ProviderActionList.as_view(), name='provider-action'),
    path(
        PROVIDER + 'action/<int:action_id>/',
        views.ProviderAction.as_view(),
        name='provider-action-details'
    ),
    path(
        PROVIDER + 'action/<int:action_id>/run/',
        views.ProviderTask.as_view(),
        name='provider-action-run'
    ),
    path(PROVIDER + 'upgrade/', views.ProviderUpgrade.as_view(), name='provider-upgrade'),
    path(
        PROVIDER + 'upgrade/<int:upgrade_id>/',
        views.ProviderUpgradeDetail.as_view(),
        name='provider-upgrade-details'
    ),
    path(
        PROVIDER + 'upgrade/<int:upgrade_id>/do/',
        views.DoProviderUpgrade.as_view(),
        name='do-provider-upgrade'
    ),
    path(PROVIDER + 'config/', include('api.config.urls'), {'object_type': 'provider'}),

    path('host/', views.HostList.as_view(), name='host'),
    path(HOST, views.HostDetail.as_view(), name='host-details'),

    path(HOST + 'action/', views.HostActionList.as_view(), name='host-action'),
    path(
        HOST + 'action/<int:action_id>/',
        views.HostAction.as_view(),
        name='host-action-details'
    ),
    path(
        HOST + 'action/<int:action_id>/run/',
        views.HostTask.as_view(),
        name='host-action-run'
    ),
    path(HOST + 'config/', include('api.config.urls'), {'object_type': 'host'}),

    path('task/', job_views.Task.as_view(), name='task'),
    path('task/<int:task_id>/', job_views.TaskDetail.as_view(), name='task-details'),
    path('task/<int:task_id>/restart/', job_views.TaskReStart.as_view(), name='task-restart'),
    path('task/<int:task_id>/cancel/', job_views.TaskCancel.as_view(), name='task-cancel'),

    path('job/', job_views.JobList.as_view(), name='job'),
    path('job/<int:job_id>/', job_views.JobDetail.as_view(), name='job-details'),
    path('job/<int:job_id>/log/', job_views.LogStorageListView.as_view(), name='log-list'),
    path('job/<int:job_id>/log/<int:log_id>/',
         job_views.LogStorageView.as_view(),
         name='log-storage'),
    path('job/<int:job_id>/log/<int:log_id>/download/',
         job_views.download_log_file,
         name='download-log'),
    path(
        'job/<int:job_id>/log/<name:tag>/<name:level>/<name:log_type>/',
        job_views.LogFile.as_view(),
        name='log-file'
    ),
    # path('docs/', include_docs_urls(title='ArenaData Chapel API')),
    path('swagger/', swagger_view),
    path('schema/', schema_view),
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),

    path('docs/md/', docs.docs_md),
    path('docs/', docs.docs_html),

    path('', views.APIRoot.as_view()),
]

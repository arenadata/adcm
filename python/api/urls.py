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

from django.urls import path, include, register_converter
from rest_framework.renderers import CoreJSONRenderer
from rest_framework.schemas import get_schema_view
from rest_framework.schemas.coreapi import SchemaGenerator

from api import views, docs
from rbac.endpoints import token

register_converter(views.NameConverter, 'name')

info_path = path('info/', views.ADCMInfo.as_view(), name='adcm-info')
stats_path = path('stats/', include('api.stats.urls'))
stack_path = path('stack/', include('api.stack.urls'))
cluster_path = path('cluster/', include('api.cluster.urls'))
service_path = path('service/', include('api.service.urls'))
component_path = path('component/', include('api.component.urls'))
provider_path = path('provider/', include('api.provider.urls'))
host_path = path('host/', include('api.host.urls'))
adcm_path = path('adcm/', include('api.adcm.urls'))
group_config_path = path('group-config/', include('api.group_config.urls'))
config_path = path('config/', include('api.object_config.urls'))
config_log_path = path('config-log/', include('api.config_log.urls'))
task_path = path('task/', include('api.job.task_urls'))
job_path = path('job/', include('api.job.urls'))
concern_path = path('concern/', include('api.concern.urls'))
auth_path = path('auth/', include('rest_framework.urls', namespace='rest_framework'))
docs_md_path = path('docs/md/', docs.docs_md)
docs_path = path('docs/', docs.docs_html)
token_path = path('token/', token.GetAuthToken.as_view(), name='token')

rbac_path = path('rbac/', include(('rbac.urls', 'rbac')))

urlpatterns = [
    path('', views.APIRoot.as_view()),
    info_path,
    stats_path,
    stack_path,
    cluster_path,
    service_path,
    component_path,
    provider_path,
    host_path,
    adcm_path,
    group_config_path,
    config_path,
    config_log_path,
    task_path,
    job_path,
    concern_path,
    auth_path,
    docs_md_path,
    docs_path,
    rbac_path,
    token_path,
    path(
        r'schema/',
        get_schema_view(
            title='ArenaData Chapel API',
            description='CoreAPI schema',
            generator_class=SchemaGenerator,
            renderer_classes=[CoreJSONRenderer],
            url='http://127.0.0.1:8000/api/v1/',
            patterns=[
                info_path,
                stats_path,
                stack_path,
                cluster_path,
                service_path,
                component_path,
                provider_path,
                host_path,
                adcm_path,
                group_config_path,
                config_path,
                config_log_path,
                task_path,
                job_path,
                concern_path,
                auth_path,
                docs_md_path,
                docs_path,
                token_path,
            ],
        ),
        name='schema',
    ),
]

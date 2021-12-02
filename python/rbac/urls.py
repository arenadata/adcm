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

"""RBAC root URLs"""

from django.urls import path, include
from rest_framework.renderers import JSONOpenAPIRenderer
from rest_framework.schemas import get_schema_view
from rest_framework.schemas.openapi import SchemaGenerator

from .endpoints import logout, root, token

user_path = path('user/', include('rbac.endpoints.user.urls'))
group_path = path('group/', include('rbac.endpoints.group.urls'))
role_path = path('role/', include('rbac.endpoints.role.urls'))
policy_path = path(r'policy/', include('rbac.endpoints.policy.urls'))
logout_path = path('logout/', logout.LogOut.as_view(), name='logout')
token_path = path('token/', token.GetAuthToken.as_view(), name='token')

urlpatterns = [
    path('', root.RBACRoot.as_view(), name='root'),
    user_path,
    group_path,
    role_path,
    policy_path,
    logout_path,
    token_path,
    path(
        r'schema/',
        get_schema_view(
            title='ArenaData Chapel API',
            description='OpenAPI Schema',
            version='1.0.0',
            url='api/v1/rbac/',
            generator_class=SchemaGenerator,
            renderer_classes=[JSONOpenAPIRenderer],
            patterns=[
                user_path,
                group_path,
                role_path,
                policy_path,
                logout_path,
                # token_path,  TODO: one View on /api/v1/ and /api/v1/rbac/ ???
            ],
        ),
        name='rbac-schema',
    ),
]

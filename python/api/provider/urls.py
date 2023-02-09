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

from api.provider.views import (
    DoProviderUpgrade,
    ProviderDetail,
    ProviderList,
    ProviderUpgrade,
    ProviderUpgradeDetail,
)
from django.urls import include, path

# fmt: off
urlpatterns = [
    path('', ProviderList.as_view(), name='provider'),
    path('<int:provider_id>/', include([
        path('', ProviderDetail.as_view(), name='provider-details'),
        path('host/', include('api.host.provider_urls')),
        path('action/', include('api.action.urls'), {'object_type': 'provider'}),
        path('config/', include('api.config.urls'), {'object_type': 'provider'}),
        path('upgrade/', include([
            path('', ProviderUpgrade.as_view(), name='provider-upgrade'),
            path('<int:upgrade_id>/', include([
                path('', ProviderUpgradeDetail.as_view(), name='provider-upgrade-details'),
                path('do/', DoProviderUpgrade.as_view(), name='do-provider-upgrade'),
            ])),
        ])),
    ])),
]
# fmt: on

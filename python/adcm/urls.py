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
"""adcm URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include
from django.urls import path

import api.urls
import api_ui.urls
import cm.adcm_config
import cm.views

urlpatterns = [
    path('cm/', cm.views.index),
    path('cm/ws_test/', cm.views.ws_test),
    path('cm/ws_test/<ws_type>/', cm.views.ws_test),
    path('cm/ws_test/<ws_type>/<dev>/', cm.views.ws_test),
    path('cm/error/<msg>/', cm.views.error),
    path('social/complete/google-oauth2/', cm.views.complete),
    path('social/', include('social_django.urls', namespace='social')),
    path(
        'api/',
        include(
            [
                path('v1/', include(api.urls)),
                path('ui/', include(api_ui.urls)),
            ]
        ),
    ),
]

cm.adcm_config.load_social_auth()

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

from cm.services.status import notify
from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from api_v2.views import ADCMGenericViewSet


class StatusServerUpdateView(ADCMGenericViewSet):
    # Endpoints

    def create(self, request, *_, **__):  # noqa: ARG002
        self.check_is_allowed(request)
        notify.update_all()
        return Response(status=HTTP_200_OK)

    # Helpers

    def check_is_allowed(self, request) -> None:
        if request.user is None or request.user.username != settings.ADCM_STATUS_USERNAME:
            raise PermissionDenied()

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

from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.request import Request
from rest_framework.response import Response

from api_v2.login.views import BaseLoginView


class TokenAuthenticationExcludingTokenAcquiring(TokenAuthentication):
    def authenticate(self, request):  # noqa: ARG002
        return


class TokenView(BaseLoginView):
    authentication_classes = (TokenAuthenticationExcludingTokenAcquiring,)

    def post(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        user = self.perform_login(request=request)
        token, _ = Token.objects.get_or_create(user=user)

        return Response({"token": token.key})

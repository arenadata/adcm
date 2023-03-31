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

from rbac.endpoints.me.serializers import MeUserSerializer
from rbac.models import User
from rbac.services.user import update
from rest_framework.generics import RetrieveUpdateAPIView


class MyselfView(RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = MeUserSerializer

    def get_object(self):
        return User.objects.get(id=self.request.user.id)

    def perform_update(self, serializer: MeUserSerializer):
        update(user=serializer.instance, context_user=self.request.user, partial=True, **serializer.validated_data)

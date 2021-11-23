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

import pytest
from rest_framework import status
from rest_framework.reverse import reverse


@pytest.mark.django_db
def test_create_role(admin_api_client):
    url = reverse('rbac:role-list')
    response = admin_api_client.post(url, data={})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

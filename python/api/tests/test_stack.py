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

from pathlib import Path

from adcm.tests.base import BaseTestCase
from cm.models import Prototype
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK


class TestPrototypeAPI(BaseTestCase):
    def test_cluster_prototype_retrieve_success(self):
        bundle = self.upload_and_load_bundle(
            path=Path(
                self.base_dir,
                "python/api/tests/files/test_actions_data.tar",
            ),
        )
        cluster_prototype = Prototype.objects.get(bundle=bundle, type="cluster")

        response: Response = self.client.get(
            path=reverse(viewname="v1:cluster-prototype-detail", kwargs={"prototype_pk": cluster_prototype.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

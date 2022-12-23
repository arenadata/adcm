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

from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase
from cm.models import (
    ADCM,
    Action,
    ActionType,
    Bundle,
    ConfigLog,
    ObjectConfig,
    Prototype,
)


class TestActionAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()

        config = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(obj_ref=config, config="{}", attr={"ldap_integration": {"active": False}})
        config.current = config_log.pk
        config.save(update_fields=["current"])

        self.adcm_prototype = Prototype.objects.create(bundle=bundle, type="adcm")
        self.adcm = ADCM.objects.create(
            prototype=self.adcm_prototype,
            name="ADCM",
            config=config,
        )
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm_prototype,
            type=ActionType.Job,
            state_available="any",
        )

    def test_retrieve(self):
        response: Response = self.client.get(
            reverse("action-detail", kwargs={"action_pk": self.action.pk}),
        )

        self.assertEqual(response.data["id"], self.action.pk)

    def test_list(self):
        response: Response = self.client.get(
            reverse("object-action", kwargs={"adcm_pk": self.adcm.pk}),
        )

        action = Action.objects.create(
            name=settings.ADCM_TURN_ON_MM_ACTION_NAME,
            prototype=self.adcm_prototype,
            type=ActionType.Job,
            state_available="any",
        )

        self.assertEqual(len(response.data), 1)
        self.assertNotIn(action.pk, {action_data["id"] for action_data in response.data})

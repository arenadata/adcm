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
from cm.models import (
    ADCM,
    Action,
    ActionType,
    Bundle,
    Cluster,
    ConfigLog,
    ObjectConfig,
    Prototype,
)
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT


class TestActionAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()

        config = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(
            obj_ref=config,
            config="{}",
            attr={"ldap_integration": {"active": False}},
        )
        config.current = config_log.pk
        config.save(update_fields=["current"])

        self.adcm_prototype = Prototype.objects.create(bundle=bundle, type="adcm")
        self.adcm = ADCM.objects.first()
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm.prototype,
            type=ActionType.JOB,
            state_available="any",
        )

    def test_retrieve(self):
        response: Response = self.client.get(
            reverse(viewname="v1:action-detail", kwargs={"action_pk": self.action.pk}),
        )

        self.assertEqual(response.data["id"], self.action.pk)

    def test_list(self):
        response: Response = self.client.get(
            reverse(viewname="v1:object-action", kwargs={"adcm_pk": self.adcm.pk}),
        )

        action = Action.objects.create(
            name=settings.ADCM_TURN_ON_MM_ACTION_NAME,
            prototype=self.adcm.prototype,
            type=ActionType.JOB,
            state_available="any",
        )

        self.assertEqual(len(response.data), 3)
        self.assertNotIn(action.pk, {action_data["id"] for action_data in response.data})

    def test_jinja_conf_success(self):
        path = Path(
            self.base_dir,
            "python/api/tests/files/bundle_test_action_with_jinja_conf.tar",
        )
        with open(file=path, encoding=settings.ENCODING_UTF_8) as f:
            response: Response = self.client.post(
                path=reverse(viewname="v1:upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(viewname="v1:load-bundle"),
            data={"bundle_file": path.name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(Action.objects.last().config_jinja, "./config.j2")

    def test_jinja_wrong_conf_fail(self):
        path = Path(
            self.base_dir,
            "python/api/tests/files/bundle_test_action_with_jinja_wrong_conf.tar",
        )
        with open(file=path, encoding=settings.ENCODING_UTF_8) as f:
            response: Response = self.client.post(
                path=reverse(viewname="v1:upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(viewname="v1:load-bundle"),
            data={"bundle_file": path.name},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_jinja_wrong_conf_path_fail(self):
        path = Path(
            self.base_dir,
            "python/api/tests/files/bundle_test_action_with_jinja_wrong_conf_path.tar",
        )
        with open(file=path, encoding=settings.ENCODING_UTF_8) as f:
            response: Response = self.client.post(
                path=reverse(viewname="v1:upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(viewname="v1:load-bundle"),
            data={"bundle_file": path.name},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_jinja_conf_serialize_success(self):
        bundle = self.upload_and_load_bundle(
            path=Path(
                self.base_dir,
                "python/api/tests/files/test_actions_data.tar",
            ),
        )

        cluster_prototype = Prototype.objects.get(bundle=bundle, type="cluster")
        cluster_response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={"name": "test_cluster", "prototype_id": cluster_prototype.pk},
        )
        cluster = Cluster.objects.get(pk=cluster_response.data["id"])

        cluster_config = ConfigLog.objects.get(pk=cluster.config.current)
        cluster_config.config["flag"] = "complex"
        cluster_config.save(update_fields=["config"])

        action = Action.objects.get(prototype=cluster_prototype)
        action.state_available = "any"
        action.save(update_fields=["state_available"])

        response: Response = self.client.get(
            path=reverse(
                viewname="v1:object-action-details", kwargs={"cluster_id": cluster.pk, "action_id": action.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.data["config"])

        response: Response = self.client.get(
            path=f'{reverse(viewname="v1:object-action", kwargs={"cluster_id": cluster.pk})}?view=interface',
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.data[0]["config"])

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

from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.api import add_host_to_cluster, save_hc
from cm.errors import AdcmEx
from cm.job import check_hostcomponentmap
from cm.models import Action, Bundle, ClusterObject, Host, Prototype, ServiceComponent
from cm.tests.test_upgrade import (
    cook_cluster,
    cook_cluster_bundle,
    cook_provider,
    cook_provider_bundle,
)


class TestHC(BaseTestCase):
    def test_action_hc_simple(self):  # pylint: disable=too-many-locals
        b1 = cook_cluster_bundle("1.0")
        cluster = cook_cluster(b1, "Test1")
        b2 = cook_provider_bundle("1.0")
        provider = cook_provider(b2, "DF01")
        h1 = Host.objects.get(provider=provider, fqdn="server01.inter.net")
        action = Action(name="run")
        hc_list, _ = check_hostcomponentmap(cluster, action, [])

        self.assertEqual(hc_list, None)

        try:
            action = Action(name="run", hostcomponentmap="qwe")
            hc_list, _ = check_hostcomponentmap(cluster, action, [])

            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, "TASK_ERROR")
            self.assertEqual(e.msg, "hc is required")

        co = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")
        sc1 = ServiceComponent.objects.get(cluster=cluster, service=co, prototype__name="server")
        try:
            action = Action(name="run", hostcomponentmap="qwe")
            hc = [{"service_id": co.id, "component_id": sc1.id, "host_id": 500}]
            hc_list, _ = check_hostcomponentmap(cluster, action, hc)

            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, "HOST_NOT_FOUND")

        try:
            action = Action(name="run", hostcomponentmap="qwe")
            hc = [{"service_id": co.id, "component_id": sc1.id, "host_id": h1.id}]
            hc_list, _ = check_hostcomponentmap(cluster, action, hc)

            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, "FOREIGN_HOST")

        add_host_to_cluster(cluster, h1)
        try:
            action = Action(name="run", hostcomponentmap="qwe")
            hc = [{"service_id": 500, "component_id": sc1.id, "host_id": h1.id}]
            hc_list, _ = check_hostcomponentmap(cluster, action, hc)

            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, "CLUSTER_SERVICE_NOT_FOUND")

        try:
            action = Action(name="run", hostcomponentmap="qwe")
            hc = [{"service_id": co.id, "component_id": 500, "host_id": h1.id}]
            hc_list, _ = check_hostcomponentmap(cluster, action, hc)

            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, "COMPONENT_NOT_FOUND")

    def test_action_hc(self):  # pylint: disable=too-many-locals
        b1 = cook_cluster_bundle("1.0")
        cluster = cook_cluster(b1, "Test1")
        b2 = cook_provider_bundle("1.0")
        provider = cook_provider(b2, "DF01")

        h1 = Host.objects.get(provider=provider, fqdn="server01.inter.net")
        h2 = Host.objects.get(provider=provider, fqdn="server02.inter.net")
        co = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")
        sc1 = ServiceComponent.objects.get(cluster=cluster, service=co, prototype__name="server")

        add_host_to_cluster(cluster, h1)
        add_host_to_cluster(cluster, h2)

        try:
            act_hc = [{"service": "hadoop", "component": "server", "action": "delete"}]
            action = Action(name="run", hostcomponentmap=act_hc)
            hc = [{"service_id": co.id, "component_id": sc1.id, "host_id": h1.id}]
            hc_list, _ = check_hostcomponentmap(cluster, action, hc)

            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, "WRONG_ACTION_HC")
            self.assertEqual(e.msg[:32], 'no permission to "add" component')

        act_hc = [{"service": "hadoop", "component": "server", "action": "add"}]
        action = Action(name="run", hostcomponentmap=act_hc)
        hc = [
            {"service_id": co.id, "component_id": sc1.id, "host_id": h1.id},
            {"service_id": co.id, "component_id": sc1.id, "host_id": h2.id},
        ]
        hc_list, _ = check_hostcomponentmap(cluster, action, hc)

        self.assertNotEqual(hc_list, None)

        save_hc(cluster, hc_list)
        act_hc = [{"service": "hadoop", "component": "server", "action": "remove"}]
        action = Action(name="run", hostcomponentmap=act_hc)
        hc = [
            {"service_id": co.id, "component_id": sc1.id, "host_id": h2.id},
        ]
        hc_list, _ = check_hostcomponentmap(cluster, action, hc)

        self.assertNotEqual(hc_list, None)

    def test_empty_hostcomponent(self):
        test_bundle_filename = "min-3199.tar"
        test_bundle_path = Path(
            settings.BASE_DIR,
            "python/cm/tests/files",
            test_bundle_filename,
        )
        with open(test_bundle_path, encoding=settings.ENCODING_UTF_8) as f:
            response: Response = self.client.post(
                path=reverse("upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": test_bundle_filename},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        bundle = Bundle.objects.get(pk=response.data["id"])
        cluster_prototype = Prototype.objects.get(bundle=bundle, type="cluster")
        service_prototype = Prototype.objects.get(bundle=bundle, type="service")

        response: Response = self.client.post(
            path=reverse("cluster"),
            data={
                "bundle_id": bundle.pk,
                "display_name": "test_cluster_display_name",
                "name": "test-cluster-name",
                "prototype_id": cluster_prototype.pk,
            },
        )
        cluster_pk = response.data["id"]

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse("service", kwargs={"cluster_id": cluster_pk}),
            data={
                "prototype_id": service_prototype.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.get(
            path=f'{reverse("host-component", kwargs={"cluster_id": cluster_pk})}?view=interface',
            extra={"view": "interface"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

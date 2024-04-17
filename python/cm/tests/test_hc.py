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

from adcm.tests.base import APPLICATION_JSON, BaseTestCase, BusinessLogicMixin
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT

from cm.api import add_host_to_cluster, save_hc
from cm.errors import AdcmEx
from cm.models import Action, Bundle, ClusterObject, Host, Prototype, ServiceComponent
from cm.services.job.checks import check_hostcomponentmap
from cm.tests.mocks.task_runner import RunTaskMock
from cm.tests.test_upgrade import (
    cook_cluster,
    cook_cluster_bundle,
    cook_provider,
    cook_provider_bundle,
)


class TestHC(BaseTestCase, BusinessLogicMixin):
    def test_action_hc_simple(self):
        bundle_1 = cook_cluster_bundle("1.0")
        cluster = cook_cluster(bundle_1, "Test1")
        bundle_2 = cook_provider_bundle("1.0")
        provider = cook_provider(bundle_2, "DF01")
        host_1 = Host.objects.get(provider=provider, fqdn="server01.inter.net")

        action = Action(name="run")
        hc_list, *_ = check_hostcomponentmap(cluster, action, [])
        self.assertEqual(hc_list, None)

        with self.assertRaises(AdcmEx) as e:
            action = Action(name="run", hostcomponentmap=["qwe"])
            hc_list, *_ = check_hostcomponentmap(cluster, action, [])
        self.assertEqual(e.exception.code, "TASK_ERROR")
        self.assertEqual(e.exception.msg, "hc is required")

        service = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")
        sc1 = ServiceComponent.objects.get(cluster=cluster, service=service, prototype__name="server")
        with self.assertRaises(AdcmEx) as e:
            action = Action(name="run", hostcomponentmap=["qwe"])
            hostcomponent = [{"service_id": service.id, "component_id": sc1.id, "host_id": 500}]
            hc_list, *_ = check_hostcomponentmap(cluster, action, hostcomponent)
        self.assertEqual(e.exception.code, "HOST_NOT_FOUND")

        with self.assertRaises(AdcmEx) as e:
            action = Action(name="run", hostcomponentmap=["qwe"])
            hostcomponent = [{"service_id": service.id, "component_id": sc1.id, "host_id": host_1.id}]
            hc_list, *_ = check_hostcomponentmap(cluster, action, hostcomponent)
        self.assertEqual(e.exception.code, "FOREIGN_HOST")

        add_host_to_cluster(cluster, host_1)
        with self.assertRaises(AdcmEx) as e:
            action = Action(name="run", hostcomponentmap="qwe")
            hostcomponent = [{"service_id": 500, "component_id": sc1.id, "host_id": host_1.id}]
            hc_list, *_ = check_hostcomponentmap(cluster, action, hostcomponent)
        self.assertEqual(e.exception.code, "CLUSTER_SERVICE_NOT_FOUND")

        with self.assertRaises(AdcmEx) as e:
            action = Action(name="run", hostcomponentmap=["qwe"])
            hostcomponent = [{"service_id": service.id, "component_id": 500, "host_id": host_1.id}]
            hc_list, *_ = check_hostcomponentmap(cluster, action, hostcomponent)
        self.assertEqual(e.exception.code, "COMPONENT_NOT_FOUND")

    def test_action_hc(self):
        bundle_1 = cook_cluster_bundle("1.0")
        cluster = cook_cluster(bundle_1, "Test1")
        bundle_2 = cook_provider_bundle("1.0")
        provider = cook_provider(bundle_2, "DF01")

        host_1 = Host.objects.get(provider=provider, fqdn="server01.inter.net")
        host_2 = Host.objects.get(provider=provider, fqdn="server02.inter.net")
        service = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")
        sc1 = ServiceComponent.objects.get(cluster=cluster, service=service, prototype__name="server")

        add_host_to_cluster(cluster, host_1)
        add_host_to_cluster(cluster, host_2)

        try:
            act_hc = [{"service": "hadoop", "component": "server", "action": "delete"}]
            action = Action(name="run", hostcomponentmap=act_hc)
            hostcomponent = [{"service_id": service.id, "component_id": sc1.id, "host_id": host_1.id}]
            hc_list, *_ = check_hostcomponentmap(cluster, action, hostcomponent)

            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, "WRONG_ACTION_HC")
            self.assertEqual(e.msg[:32], 'no permission to "add" component')

        act_hc = [{"service": "hadoop", "component": "server", "action": "add"}]
        action = Action(name="run", hostcomponentmap=act_hc)
        hostcomponent = [
            {"service_id": service.id, "component_id": sc1.id, "host_id": host_1.id},
            {"service_id": service.id, "component_id": sc1.id, "host_id": host_2.id},
        ]
        hc_list, *_ = check_hostcomponentmap(cluster, action, hostcomponent)

        self.assertNotEqual(hc_list, None)

        save_hc(cluster, hc_list)
        act_hc = [{"service": "hadoop", "component": "server", "action": "remove"}]
        action = Action(name="run", hostcomponentmap=act_hc)
        hostcomponent = [
            {"service_id": service.id, "component_id": sc1.id, "host_id": host_2.id},
        ]
        hc_list, *_ = check_hostcomponentmap(cluster, action, hostcomponent)

        self.assertNotEqual(hc_list, None)

    def test_empty_hostcomponent(self):
        test_bundle_filename = "min-3199.tar"
        test_bundle_path = Path(
            self.base_dir,
            "python/cm/tests/files",
            test_bundle_filename,
        )
        with open(test_bundle_path, encoding=settings.ENCODING_UTF_8) as f:
            response: Response = self.client.post(
                path=reverse(viewname="v1:upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(viewname="v1:load-bundle"),
            data={"bundle_file": test_bundle_filename},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        bundle = Bundle.objects.get(pk=response.data["id"])
        cluster_prototype = Prototype.objects.get(bundle=bundle, type="cluster")
        service_prototype = Prototype.objects.get(bundle=bundle, type="service")

        response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
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
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster_pk}),
            data={
                "prototype_id": service_prototype.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.get(
            path=f'{reverse(viewname="v1:host-component", kwargs={"cluster_id": cluster_pk})}?view=interface',
            extra={"view": "interface"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_run_same_hc_bug_adcm_4929(self) -> None:
        bundles_dir = Path(__file__).parent / "bundles"
        bundle = self.add_bundle(bundles_dir / "cluster_1")
        cluster = self.add_cluster(bundle=bundle, name="Cool")
        service_1 = self.add_services_to_cluster(["service_one_component"], cluster=cluster).get()
        service_2 = self.add_services_to_cluster(["service_two_components"], cluster=cluster).get()
        service_with_action = self.add_services_to_cluster(["with_hc_acl_actions"], cluster=cluster).get()

        hostprovider = self.add_provider(bundle=self.add_bundle(bundles_dir / "provider"), name="prov")
        host_1 = self.add_host(provider=hostprovider, fqdn="host-1")
        host_2 = self.add_host(provider=hostprovider, fqdn="host-2")

        self.add_host_to_cluster(cluster.pk, host_1.pk)
        self.add_host_to_cluster(cluster.pk, host_2.pk)

        component_1_1 = ServiceComponent.objects.get(service=service_1, prototype__name="component_1")
        component_2_1 = ServiceComponent.objects.get(service=service_2, prototype__name="component_1")
        component_2_2 = ServiceComponent.objects.get(service=service_2, prototype__name="component_2")
        hc = self.set_hostcomponent(
            cluster=cluster,
            entries=(
                (host_1, component_1_1),
                (host_1, component_2_1),
                (host_1, component_2_2),
                (host_2, component_2_1),
                (host_2, component_2_2),
            ),
        )
        action = Action.objects.get(prototype=service_with_action.prototype, name="with_hc")

        with RunTaskMock() as run_task:
            response = self.client.post(
                path=f"/api/v2/clusters/{cluster.id}/services/{service_with_action.id}/actions/{action.id}/run/",
                data={
                    "hostComponentMap": [{"hostId": entry.host_id, "componentId": entry.component_id} for entry in hc],
                },
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["desc"], "Host-component is expected to be changed for this action")
        self.assertIsNone(run_task.target_task)

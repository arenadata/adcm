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

from django.test import TestCase

import cm.api
import cm.job
from cm.models import Host, ClusterObject, ServiceComponent, Action
from cm.errors import AdcmEx
from cm.tests_upgrade import SetUp


class TestHC(TestCase):

    def test_action_hc_simple(self):   # pylint: disable=too-many-locals
        setup = SetUp()
        b1 = setup.cook_cluster_bundle('1.0')
        cluster = setup.cook_cluster(b1, 'Test1')
        b2 = setup.cook_provider_bundle('1.0')
        provider = setup.cook_provider(b2, "DF01")
        h1 = Host.objects.get(provider=provider, fqdn='server01.inter.net')

        action = Action(name="run")
        (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, [])
        self.assertEqual(hc_list, None)

        try:
            action = Action(name="run", hostcomponentmap='qwe')
            (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, [])
            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, 'TASK_ERROR')
            self.assertEqual(e.msg, 'hc is required')

        co = ClusterObject.objects.get(cluster=cluster, prototype__name='hadoop')
        sc1 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='server')
        try:
            action = Action(name="run", hostcomponentmap='qwe')
            hc = [{"service_id": co.id, "component_id": sc1.id, "host_id": 500}]
            (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, hc)
            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, 'HOST_NOT_FOUND')

        try:
            action = Action(name="run", hostcomponentmap='qwe')
            hc = [{"service_id": co.id, "component_id": sc1.id, "host_id": h1.id}]
            (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, hc)
            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, 'FOREIGN_HOST')

        cm.api.add_host_to_cluster(cluster, h1)
        try:
            action = Action(name="run", hostcomponentmap="qwe")
            hc = [{"service_id": 500, "component_id": sc1.id, "host_id": h1.id}]
            (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, hc)
            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, 'SERVICE_NOT_FOUND')

        try:
            action = Action(name="run", hostcomponentmap="qwe")
            hc = [{"service_id": co.id, "component_id": 500, "host_id": h1.id}]
            (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, hc)
            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, 'COMPONENT_NOT_FOUND')

    def test_action_hc(self):   # pylint: disable=too-many-locals
        setup = SetUp()
        b1 = setup.cook_cluster_bundle('1.0')
        cluster = setup.cook_cluster(b1, 'Test1')
        b2 = setup.cook_provider_bundle('1.0')
        provider = setup.cook_provider(b2, "DF01")

        h1 = Host.objects.get(provider=provider, fqdn='server01.inter.net')
        h2 = Host.objects.get(provider=provider, fqdn='server02.inter.net')
        co = ClusterObject.objects.get(cluster=cluster, prototype__name='hadoop')
        sc1 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='server')

        cm.api.add_host_to_cluster(cluster, h1)
        cm.api.add_host_to_cluster(cluster, h2)

        try:
            act_hc = [{'service': 'hadoop', 'component': 'server', 'action': 'delete'}]
            action = Action(name="run", hostcomponentmap=act_hc)
            hc = [{"service_id": co.id, "component_id": sc1.id, "host_id": h1.id}]
            (hc_list, delta) = cm.job.check_hostcomponentmap(cluster, action, hc)
            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, 'WRONG_ACTION_HC')
            self.assertEqual(e.msg[:32], 'no permission to "add" component')

        act_hc = [{'service': 'hadoop', 'component': 'server', 'action': 'add'}]
        action = Action(name="run", hostcomponentmap=act_hc)
        hc = [
            {"service_id": co.id, "component_id": sc1.id, "host_id": h1.id},
            {"service_id": co.id, "component_id": sc1.id, "host_id": h2.id},
        ]
        (hc_list, delta) = cm.job.check_hostcomponentmap(cluster, action, hc)
        self.assertNotEqual(hc_list, None)
        self.assertEqual(delta['remove'], {})
        group = '{}.{}'.format(co.prototype.name, sc1.component.name)
        self.assertEqual(delta['add'][group]['server01.inter.net'], h1)
        self.assertEqual(delta['add'][group]['server02.inter.net'], h2)

        cm.api.save_hc(cluster, hc_list)
        act_hc = [{'service': 'hadoop', 'component': 'server', 'action': 'remove'}]
        action = Action(name="run", hostcomponentmap=act_hc)
        hc = [
            {"service_id": co.id, "component_id": sc1.id, "host_id": h2.id},
        ]
        (hc_list, delta) = cm.job.check_hostcomponentmap(cluster, action, hc)
        self.assertNotEqual(hc_list, None)
        self.assertEqual(delta['add'], {})
        group = '{}.{}'.format(co.prototype.name, sc1.component.name)
        self.assertEqual(delta['remove'][group]['server01.inter.net'], h1)

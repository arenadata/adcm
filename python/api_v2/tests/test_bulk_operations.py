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
from itertools import chain, product

from cm.models import (
    ClusterObject,
    ConfigLog,
    ObjectConfig,
    ObjectType,
    ServiceComponent,
)
from rbac.services.user import create_user
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK

from api_v2.tests.base import BaseAPITestCase


class TestBulkAddServices(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

        self.initial_object_config_pks = list(ObjectConfig.objects.values_list("pk", flat=True))
        self.initial_config_log_pks = list(ConfigLog.objects.values_list("pk", flat=True))

    def test_config_objects(self):
        services_qs = self.add_services_to_cluster(
            service_names=[
                "service_5_variant_type_without_values",
                "service_4_save_config_without_required_field",
                "service_1",
            ],
            cluster=self.cluster_1,
        )
        self.assertEqual(services_qs.count(), 3)
        components_qs = ServiceComponent.objects.filter(service__in=services_qs, cluster=self.cluster_1)
        self.assertEqual(components_qs.count(), 2)

        new_object_configs = ObjectConfig.objects.exclude(pk__in=self.initial_object_config_pks)
        new_config_logs = ConfigLog.objects.exclude(pk__in=self.initial_config_log_pks)

        # 3 services, 2 components
        self.assertEqual(new_object_configs.count(), 5)
        self.assertEqual(new_config_logs.count(), 5)

        self.assertTrue(
            all(
                (obj_conf.previous == 0)
                and (obj_conf.current != 0)
                and (obj_conf.current in new_config_logs.values_list("pk", flat=True))
                for obj_conf in new_object_configs
            )
        )
        self.assertTrue(all(obj_conf.object in chain(services_qs, components_qs) for obj_conf in new_object_configs))
        self.assertTrue(all(config_log.obj_ref in new_object_configs for config_log in new_config_logs))

    def test_permission_reappliance(self):
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Cluster Administrator"):
            services_qs = self.add_services_to_cluster(
                service_names=[
                    "service_5_variant_type_without_values",
                    "service_4_save_config_without_required_field",
                    "service_1",
                ],
                cluster=self.cluster_1,
            )
            components_qs = ServiceComponent.objects.filter(service__in=services_qs, cluster=self.cluster_1)
            self.client.login(**self.test_user_credentials)

            for request_type, obj in product(["object", "config"], chain(services_qs, components_qs)):
                obj: ClusterObject | ServiceComponent
                if obj.prototype.type == ObjectType.SERVICE:
                    if request_type == "object":
                        viewname = "v2:service-detail"
                        kwargs = {"cluster_pk": self.cluster_1.pk, "pk": obj.pk}
                    elif request_type == "config":
                        viewname = "v2:service-config-list"
                        kwargs = {"cluster_pk": self.cluster_1.pk, "service_pk": obj.pk}
                elif obj.prototype.type == ObjectType.COMPONENT:
                    if request_type == "object":
                        viewname = "v2:component-detail"
                        kwargs = {"cluster_pk": self.cluster_1.pk, "service_pk": obj.service.pk, "pk": obj.pk}
                    elif request_type == "config":
                        viewname = "v2:component-config-list"
                        kwargs = {"cluster_pk": self.cluster_1.pk, "service_pk": obj.service.pk, "component_pk": obj.pk}
                else:
                    raise AssertionError("Wrong object type")

                with self.subTest(f"View: {viewname}, kwargs: {kwargs}"):
                    response: Response = self.client.get(path=reverse(viewname=viewname, kwargs=kwargs))
                    self.assertEqual(response.status_code, HTTP_200_OK)

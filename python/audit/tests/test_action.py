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


from datetime import datetime
from unittest.mock import patch

from adcm.tests.base import BaseTestCase
from cm.models import (
    ADCM,
    Action,
    Bundle,
    Cluster,
    Component,
    ConfigLog,
    Host,
    Prototype,
    Service,
    TaskLog,
)
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from rbac.models import Policy, Role, User
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)


class TestActionAudit(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.adcm = ADCM.objects.first()
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm.prototype,
            type="job",
            state_available="any",
        )
        self.task = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
            action=self.action,
        )
        self.action_create_view = "api.action.views.create"

    def get_cluster_service_component(self) -> tuple[Cluster, Service, Component]:
        cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(bundle=self.bundle, type="cluster"),
            name="test_cluster",
        )
        service = Service.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="service",
                display_name="test_service",
            ),
            cluster=cluster,
        )
        component = Component.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="component",
                display_name="test_component",
            ),
            cluster=cluster,
            service=service,
            config=self.adcm.config,
        )

        return cluster, service, component

    def check_obj_updated(
        self,
        log: AuditLog,
        obj_pk: int,
        obj_name: str,
        obj_type: AuditObjectType,
        operation_name: str,
        operation_result: str,
        user: User | None = None,
    ):
        if log.audit_object:
            self.assertEqual(log.audit_object.object_id, obj_pk)
            self.assertEqual(log.audit_object.object_name, obj_name)
            self.assertEqual(log.audit_object.object_type, obj_type)
            self.assertFalse(log.audit_object.is_deleted)
        else:
            self.assertFalse(log.audit_object)

        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)

        if log.user:
            self.assertEqual(log.user.username, user.username)

        self.assertEqual(log.object_changes, {})

    def test_adcm_launch(self):
        config_log = ConfigLog.objects.get(obj_ref=self.adcm.config)
        config_log.attr["ldap_integration"]["active"] = True
        config_log.save(update_fields=["attr"])

        with patch(self.action_create_view, return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(viewname="v1:run-task", kwargs={"adcm_pk": self.adcm.pk, "action_id": self.action.pk})
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_obj_updated(
            log=log,
            obj_pk=self.adcm.pk,
            obj_name=self.adcm.name,
            obj_type=AuditObjectType.ADCM,
            operation_name=f"{self.action.display_name} action launched",
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

        with patch(self.action_create_view, return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(path=reverse(viewname="v1:run-task", kwargs={"adcm_pk": 999, "action_id": self.action.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_obj_updated(
            log=log,
            obj_pk=self.adcm.pk,
            obj_name=self.adcm.name,
            obj_type=AuditObjectType.ADCM,
            operation_name=f"{self.action.display_name} action launched",
            operation_result=AuditLogOperationResult.DENIED,
            user=self.test_user,
        )

    # todo test finalizing action launch with audit
    # def test_adcm_finish_fail(self):
    #     finish_task(task=self.task, job=None, status="fail")
    #
    #     log: AuditLog = AuditLog.objects.order_by("operation_time").last()
    #
    #     self.check_obj_updated(
    #         log=log,
    #         obj_pk=self.adcm.pk,
    #         obj_name=self.adcm.name,
    #         obj_type=AuditObjectType.ADCM,
    #         operation_name=f"{self.action.display_name} action completed",
    #         operation_result=AuditLogOperationResult.FAIL,
    #     )

    def test_component_launch(self):
        cluster, service, component = self.get_cluster_service_component()
        with patch(self.action_create_view, return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    viewname="v1:run-task",
                    kwargs={
                        "cluster_id": cluster.pk,
                        "service_id": service.pk,
                        "component_id": component.pk,
                        "action_id": self.action.pk,
                    },
                ),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_obj_updated(
            log=log,
            obj_pk=component.pk,
            obj_type=AuditObjectType.COMPONENT,
            obj_name=f"{cluster.name}/{service.display_name}/{component.display_name}",
            operation_name=f"{self.action.display_name} action launched",
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_component_launch_denied(self):
        cluster, service, component = self.get_cluster_service_component()
        with (
            patch(self.action_create_view, return_value=Response(status=HTTP_201_CREATED)),
            self.no_rights_user_logged_in,
        ):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v1:run-task",
                    kwargs={
                        "cluster_id": cluster.pk,
                        "service_id": service.pk,
                        "component_id": component.pk,
                        "action_id": self.action.pk,
                    },
                ),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_obj_updated(
            log=log,
            obj_pk=component.pk,
            obj_type=AuditObjectType.COMPONENT,
            obj_name=f"{cluster.name}/{service.display_name}/{component.display_name}",
            operation_name=f"{self.action.display_name} action launched",
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_host_denied(self):
        host = Host.objects.create(
            fqdn="test_host",
            prototype=Prototype.objects.create(bundle=self.bundle, type="host"),
        )
        host_role = Role.objects.get(name="View host configurations")
        host_policy = Policy.objects.create(name="test_host_policy", role=host_role)
        host_policy.group.add(self.no_rights_user_group)
        host_policy.add_object(host)
        host_policy.apply()

        cluster, service, component = self.get_cluster_service_component()
        component_role = Role.objects.get(name="View component configurations")
        component_policy = Policy.objects.create(name="test_component_policy", role=component_role)
        component_policy.group.add(self.no_rights_user_group)
        component_policy.add_object(component)
        component_policy.apply()

        paths = [
            reverse(viewname="v1:run-task", kwargs={"adcm_pk": self.adcm.pk, "action_id": self.action.pk}),
            reverse(viewname="v1:run-task", kwargs={"cluster_id": cluster.pk, "action_id": self.action.pk}),
            reverse(viewname="v1:run-task", kwargs={"host_id": host.pk, "action_id": self.action.pk}),
            reverse(viewname="v1:run-task", kwargs={"component_id": component.pk, "action_id": self.action.pk}),
            reverse(
                viewname="v1:run-task",
                kwargs={
                    "service_id": service.pk,
                    "component_id": component.pk,
                    "action_id": self.action.pk,
                },
            ),
            reverse(
                viewname="v1:run-task",
                kwargs={
                    "cluster_id": cluster.pk,
                    "service_id": service.pk,
                    "component_id": component.pk,
                    "action_id": self.action.pk,
                },
            ),
        ]

        with (
            patch(self.action_create_view, return_value=Response(status=HTTP_201_CREATED)),
            self.no_rights_user_logged_in,
        ):
            for path in paths:
                response: Response = self.client.post(path=path)

                log: AuditLog = AuditLog.objects.order_by("operation_time").last()

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
                self.assertEqual(log.operation_result, AuditLogOperationResult.DENIED)

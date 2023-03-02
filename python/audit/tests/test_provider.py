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

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import (
    Action,
    Bundle,
    ConfigLog,
    Host,
    HostProvider,
    ObjectConfig,
    Prototype,
    Upgrade,
)
from django.urls import reverse
from rbac.models import Policy, Role, User
from rbac.upgrade.role import init_roles
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestProviderAudit(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.prototype = Prototype.objects.create(bundle=self.bundle, type="provider")
        self.name = "test_provider"
        self.provider_created_str = "Provider created"

    def check_provider_updated(
        self,
        log: AuditLog,
        provider: HostProvider,
        operation_result: AuditLogOperationResult,
        user: User,
    ) -> None:
        self.assertEqual(log.audit_object.object_id, provider.pk)
        self.assertEqual(log.audit_object.object_name, provider.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.PROVIDER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, "Provider configuration updated")
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, {})

    def check_provider_deleted(
        self,
        log: AuditLog,
        provider: HostProvider,
        operation_result: AuditLogOperationResult,
        user: User,
    ) -> None:
        self.assertEqual(log.audit_object.object_id, provider.pk)
        self.assertEqual(log.audit_object.object_name, provider.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.PROVIDER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, "Provider deleted")
        self.assertEqual(log.operation_type, AuditLogOperationType.DELETE)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, {})

    def check_action_log(self, log: AuditLog, provider: HostProvider, operation_name: str) -> None:
        self.assertEqual(log.audit_object.object_id, provider.pk)
        self.assertEqual(log.audit_object.object_name, provider.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.PROVIDER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.SUCCESS)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.object_changes, {})

    def test_create(self):
        response: Response = self.client.post(
            path=reverse("provider"),
            data={
                "name": self.name,
                "prototype_id": self.prototype.pk,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(log.audit_object.object_id, response.data["id"])
        self.assertEqual(log.audit_object.object_name, self.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.PROVIDER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, self.provider_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.CREATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.SUCCESS)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.test_user.pk)
        self.assertEqual(log.object_changes, {})

        self.client.post(
            path=reverse("provider"),
            data={
                "name": self.name,
                "prototype_id": self.prototype.id,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.provider_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.CREATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.FAIL)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.test_user.pk)
        self.assertEqual(log.object_changes, {})

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse("provider"),
                data={
                    "name": self.name,
                    "prototype_id": self.prototype.pk,
                },
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.provider_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.CREATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.DENIED)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.no_rights_user.pk)
        self.assertEqual(log.object_changes, {})

    def test_delete(self):
        provider = HostProvider.objects.create(
            name="test_provider",
            prototype=self.prototype,
        )
        self.client.delete(path=reverse("provider-details", kwargs={"provider_id": provider.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_provider_deleted(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_delete_denied(self):
        provider = HostProvider.objects.create(
            name="test_provider",
            prototype=self.prototype,
        )
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse("provider-details", kwargs={"provider_id": provider.pk}),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_provider_deleted(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_delete_denied_view_permission(self):
        provider = HostProvider.objects.create(
            name="test_provider",
            prototype=self.prototype,
        )

        init_roles()
        role = Role.objects.get(name="View provider configurations")
        policy = Policy.objects.create(name="test_policy", role=role)
        policy.user.add(self.no_rights_user)
        policy.add_object(provider)
        policy.apply()

        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse("provider-details", kwargs={"provider_id": provider.pk}),
                content_type=APPLICATION_JSON,
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertIsNotNone(log.audit_object)
        self.check_provider_deleted(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_delete_failed(self):
        provider = HostProvider.objects.create(
            name="test_provider",
            prototype=self.prototype,
        )
        Host.objects.create(
            fqdn="test_fqdn",
            prototype=Prototype.objects.create(bundle=self.bundle, type="host"),
            provider=provider,
        )

        self.client.delete(path=reverse("provider-details", kwargs={"provider_id": provider.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_provider_deleted(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.FAIL,
            user=self.test_user,
        )

    def test_update_and_restore(self):
        config = ObjectConfig.objects.create(current=0, previous=0)
        provider = HostProvider.objects.create(prototype=self.prototype, name="test_provider", config=config)

        config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = config_log.pk
        config.save(update_fields=["current"])

        self.client.post(
            path=reverse("config-history", kwargs={"provider_id": provider.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_provider_updated(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

        response: Response = self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={"provider_id": provider.pk, "version": config_log.pk},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_provider_updated(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_update_and_restore_denied(self):
        config = ObjectConfig.objects.create(current=1, previous=1)
        provider = HostProvider.objects.create(prototype=self.prototype, name="test_provider", config=config)

        ConfigLog.objects.create(obj_ref=config, config="{}")
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse("config-history", kwargs={"provider_id": provider.pk}),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_provider_updated(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(
                    "config-history-version-restore",
                    kwargs={"provider_id": provider.pk, "version": 1},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_provider_updated(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_action_launch(self):
        provider = HostProvider.objects.create(
            name="test_provider",
            prototype=self.prototype,
        )
        action = Action.objects.create(
            display_name="test_component_action",
            prototype=self.prototype,
            type="job",
            state_available="any",
        )
        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(path=reverse("run-task", kwargs={"provider_id": provider.pk, "action_id": action.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log, provider=provider, operation_name=f"{action.display_name} action launched")

    def test_do_upgrade(self):
        provider = HostProvider.objects.create(
            name="test_provider",
            prototype=self.prototype,
        )
        action = Action.objects.create(
            display_name="test_component_action",
            prototype=self.prototype,
            type="job",
            state_available="any",
        )
        upgrade = Upgrade.objects.create(
            name="test_upgrade",
            bundle=self.bundle,
            action=action,
            min_version="1",
            max_version="99",
        )

        with patch("api.provider.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    "do-provider-upgrade",
                    kwargs={"provider_id": provider.pk, "upgrade_id": upgrade.pk},
                ),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(
            log=log,
            provider=provider,
            operation_name=f"{upgrade.action.display_name} upgrade launched",
        )

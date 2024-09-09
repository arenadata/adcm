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

from http.cookies import SimpleCookie
from importlib import import_module
from pathlib import Path
from shutil import rmtree
from typing import Any, TypeAlias

from adcm.tests.base import BusinessLogicMixin, ParallelReadyTestCase
from adcm.tests.client import ADCMTestClient
from audit.models import AuditLog, AuditObjectType, AuditSession
from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    Bundle,
    Cluster,
    ClusterObject,
    ConfigLog,
    Host,
    HostProvider,
    JobLog,
    JobStatus,
    ServiceComponent,
    TaskLog,
)
from cm.tests.mocks.task_runner import RunTaskMock
from django.conf import settings
from django.http import HttpRequest
from init_db import init
from rbac.models import Group, Policy, Role, User
from rbac.upgrade.role import init_roles
from rest_framework.test import APITestCase

AuditTarget: TypeAlias = (
    Bundle
    | Cluster
    | ClusterObject
    | ServiceComponent
    | ActionHostGroup
    | HostProvider
    | Host
    | User
    | Group
    | Role
    | Policy
)


class BaseAPITestCase(APITestCase, ParallelReadyTestCase, BusinessLogicMixin):
    client: ADCMTestClient
    client_class = ADCMTestClient

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_bundles_dir = Path(__file__).parent / "bundles"
        cls.test_files_dir = Path(__file__).parent / "files"

        init_roles()
        init()

        adcm = ADCM.objects.first()
        config_log = ConfigLog.objects.get(id=adcm.config.current)
        config_log.config["auth_policy"]["max_password_length"] = 20
        config_log.save(update_fields=["config"])

    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        cluster_bundle_1_path = self.test_bundles_dir / "cluster_one"
        cluster_bundle_2_path = self.test_bundles_dir / "cluster_two"
        provider_bundle_path = self.test_bundles_dir / "provider"

        self.bundle_1 = self.add_bundle(source_dir=cluster_bundle_1_path)
        self.bundle_2 = self.add_bundle(source_dir=cluster_bundle_2_path)
        self.provider_bundle = self.add_bundle(source_dir=provider_bundle_path)

        self.cluster_1 = self.add_cluster(bundle=self.bundle_1, name="cluster_1", description="cluster_1")
        self.cluster_2 = self.add_cluster(bundle=self.bundle_2, name="cluster_2", description="cluster_2")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider", description="provider")

    def tearDown(self) -> None:
        dirs_to_clear = (
            *Path(settings.BUNDLE_DIR).iterdir(),
            *Path(settings.DOWNLOAD_DIR).iterdir(),
            *Path(settings.FILE_DIR).iterdir(),
            *Path(settings.LOG_DIR).iterdir(),
            *Path(settings.RUN_DIR).iterdir(),
            *Path(settings.VAR_DIR).iterdir(),
        )

        for item in dirs_to_clear:
            if item.is_dir():
                rmtree(item)
            else:
                if item.name != ".gitkeep":
                    item.unlink()

    def check_last_audit_record(
        self,
        model: type[AuditLog | AuditSession] = AuditLog,
        *,
        expect_object_changes_: bool = True,
        **kwargs,
    ) -> AuditLog:
        last_audit_record = model.objects.order_by("pk").last()
        self.assertIsNotNone(last_audit_record, f"{model.__name__} table is empty")

        # we always want to check who performed the audited action
        if model is AuditLog:
            kwargs.setdefault("user__username", "admin")

        object_changes = kwargs.pop("object_changes", {})

        expected_record = model.objects.filter(**kwargs).order_by("pk").last()
        self.assertIsNotNone(expected_record, "Can't find audit record")
        self.assertEqual(last_audit_record.pk, expected_record.pk, "Expected audit record is not last")

        # Object changes are {} for most cases,
        # we always want to check it, but providing it each time is redundant.
        # But sometimes structure is too complex for sqlite/ORM to handle,
        # so we have to check changes separately.
        #
        # Check is on equality after retrieve for more clear message
        # and to avoid object changes filtering
        if (model is AuditLog) and expect_object_changes_:
            self.assertDictEqual(expected_record.object_changes, object_changes)

        return last_audit_record

    @staticmethod
    def get_most_recent_audit_log() -> AuditLog | None:
        """Mostly for debug purposes"""
        return AuditLog.objects.order_by("pk").last()

    def prepare_audit_object_arguments(
        self,
        expected_object: AuditTarget | None,
        *,
        is_deleted: bool = False,
    ) -> dict[str, Any]:
        if expected_object is None:
            return {"audit_object__isnull": True}

        if isinstance(expected_object, ActionHostGroup):
            owner_name = self.prepare_audit_object_arguments(expected_object=expected_object.object)[
                "audit_object__object_name"
            ]
            name = f"{owner_name}/{expected_object.name}"
            type_ = AuditObjectType.ACTION_HOST_GROUP
        elif isinstance(expected_object, ServiceComponent):
            name = (
                f"{expected_object.cluster.name}/{expected_object.service.display_name}/{expected_object.display_name}"
            )
            type_ = "component"
        elif isinstance(expected_object, ClusterObject):
            name = f"{expected_object.cluster.name}/{expected_object.display_name}"
            type_ = "service"
        elif isinstance(expected_object, Host):
            name = expected_object.fqdn
            type_ = "host"
        elif isinstance(expected_object, Group):
            name = expected_object.name
            type_ = "group"
        elif isinstance(expected_object, Role):
            name = expected_object.name
            type_ = "role"
        else:
            name = getattr(expected_object, "display_name", expected_object.name)
            # replace for hostprovider
            type_ = expected_object.__class__.__name__.lower().replace("hostp", "p")

        return {
            "audit_object__object_id": expected_object.pk,
            "audit_object__object_name": name,
            "audit_object__object_type": type_,
            "audit_object__is_deleted": is_deleted,
        }

    @property
    def session(self):
        """Return the current session variables."""
        engine = import_module(settings.SESSION_ENGINE)
        cookie = self.cookies.get(settings.SESSION_COOKIE_NAME)
        if cookie:
            return engine.SessionStore(cookie.value)
        session = engine.SessionStore()
        session.save()
        self.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        return session

    def logout(self):
        """Log out the user by removing the cookies and session object."""
        from django.contrib.auth import get_user, logout

        request = HttpRequest()
        if self.session:
            request.session = self.session
            request.user = get_user(request)
        else:
            engine = import_module(settings.SESSION_ENGINE)
            request.session = engine.SessionStore()
        logout(request)
        self.cookies = SimpleCookie()

    def simulate_finished_task(
        self, object_: Cluster | ClusterObject | ServiceComponent, action: Action
    ) -> (TaskLog, JobLog):
        with RunTaskMock() as run_task:
            (self.client.v2[object_] / "actions" / action / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
            )

        run_task.run()
        run_task.target_task.refresh_from_db()

        return run_task.target_task, run_task.target_task.joblog_set.last()

    def simulate_running_task(
        self, object_: Cluster | ClusterObject | ServiceComponent, action: Action
    ) -> (TaskLog, JobLog):
        with RunTaskMock() as run_task:
            (self.client.v2[object_] / "actions" / action / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
            )

        run_task.run()
        run_task.target_task.refresh_from_db()
        task = run_task.target_task
        job = task.joblog_set.last()
        task.status = JobStatus.RUNNING
        task.save(update_fields=["status"])
        job.status = JobStatus.RUNNING
        job.pid = 5_000_000
        job.save(update_fields=["status", "pid"])

        return task, job

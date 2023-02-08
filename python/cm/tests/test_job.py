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
from signal import SIGTERM
from unittest.mock import Mock, patch
from urllib.parse import urljoin

from cm.api import add_cluster, add_service_to_cluster
from cm.job import (
    check_cluster,
    check_service_task,
    cook_script,
    get_adcm_config,
    get_bundle_root,
    get_state,
    prepare_context,
    prepare_job,
    prepare_job_config,
    re_prepare_job,
    restore_hc,
    set_action_state,
    set_job_status,
    set_task_status,
)
from cm.models import (
    ADCM,
    Action,
    Bundle,
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    JobLog,
    JobStatus,
    Prototype,
    ServiceComponent,
    SubAction,
    TaskLog,
)
from cm.tests.utils import (
    gen_action,
    gen_bundle,
    gen_cluster,
    gen_job_log,
    gen_prototype,
    gen_task_log,
)
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from init_db import init
from rbac.upgrade.role import init_roles
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestJob(BaseTestCase):
    # pylint: disable=too-many-public-methods

    def setUp(self):
        self.files_dir = settings.BASE_DIR / "python" / "cm" / "tests" / "files"
        self.multijob_bundle = "multijob_cluster.tar"
        self.multijob_cluster_name = "multijob_cluster"
        self.test_user_username = "admin"
        self.test_user_password = "admin"
        self.job_fake_pid = 9999

    # some tests do not need client / manually create `ADCM` object
    @staticmethod
    def init_adcm():
        init()
        init_roles()

    def create_multijob_cluster(self) -> Response:
        bundle_id = self.upload_and_load_bundle(path=Path(self.files_dir, self.multijob_bundle)).pk

        return self.client.post(
            path=reverse("cluster"),
            data={
                "prototype_id": Prototype.objects.get(name=self.multijob_cluster_name).pk,
                "name": self.multijob_cluster_name,
                "display_name": self.multijob_cluster_name,
                "bundle_id": bundle_id,
            },
            content_type=APPLICATION_JSON,
        )

    def get_cluster_action(self, cluster_id: int, action_name: str) -> tuple[Response, dict | None]:
        response: Response = self.client.get(
            path=reverse("object-action", kwargs={"cluster_id": cluster_id, "object_type": "cluster"}),
            content_type=APPLICATION_JSON,
        )

        target_action = None
        for action in response.json():
            if action["name"] == action_name:
                target_action = action
                break

        return response, target_action

    def run_action_get_target_job(
        self, action: dict, job_display_name: str, force_job_status: JobStatus | None = None
    ) -> tuple[Response, dict | None]:
        response: Response = self.client.post(path=urljoin(action["url"], "run/"), content_type=APPLICATION_JSON)

        target_job = None
        for job in response.json()["jobs"]:
            if job["display_name"] == job_display_name:
                target_job = job
                break

        if target_job is not None and force_job_status is not None:
            JobLog.objects.filter(pk=target_job["id"]).update(status=force_job_status, pid=self.job_fake_pid)

        return response, target_job

    def test_set_job_status(self):
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        action = Action.objects.create(prototype=prototype)
        job = JobLog.objects.create(action=action, start_date=timezone.now(), finish_date=timezone.now())
        status = JobStatus.RUNNING
        pid = 10
        event = Mock()

        set_job_status(job.id, status, event, pid)

        job = JobLog.objects.get(id=job.id)

        self.assertEqual(job.status, status)
        self.assertEqual(job.pid, pid)
        event.set_job_status.assert_called_once_with(job=job, status=status)

    def test_set_task_status(self):
        event = Mock()
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        action = Action.objects.create(prototype=prototype)
        task = TaskLog.objects.create(action=action, object_id=1, start_date=timezone.now(), finish_date=timezone.now())

        set_task_status(task, JobStatus.RUNNING, event)

        self.assertEqual(task.status, JobStatus.RUNNING)
        event.set_task_status.assert_called_once_with(task=task, status=JobStatus.RUNNING)

    def test_get_state_single_job(self):
        bundle = gen_bundle()
        cluster_proto = gen_prototype(bundle, "cluster")
        cluster = gen_cluster(prototype=cluster_proto)
        action = gen_action(prototype=cluster_proto)
        action.state_on_success = "success"
        action.state_on_fail = "fail"
        action.multi_state_on_success_set = ["success"]
        action.multi_state_on_success_unset = ["success unset"]
        action.multi_state_on_fail_set = ["fail"]
        action.multi_state_on_fail_unset = ["fail unset"]
        action.save()
        task = gen_task_log(cluster, action)
        job = gen_job_log(task)

        # status: expected state, expected multi_state set, expected multi_state unset
        test_data = [
            [JobStatus.SUCCESS, "success", ["success"], ["success unset"]],
            [JobStatus.FAILED, "fail", ["fail"], ["fail unset"]],
            [JobStatus.ABORTED, None, [], []],
        ]
        for status, exp_state, exp_m_state_set, exp_m_state_unset in test_data:
            state, m_state_set, m_state_unset = get_state(action, job, status)

            self.assertEqual(state, exp_state)
            self.assertListEqual(m_state_set, exp_m_state_set)
            self.assertListEqual(m_state_unset, exp_m_state_unset)

    def test_get_state_multi_job(self):
        bundle = gen_bundle()
        cluster_proto = gen_prototype(bundle, "cluster")
        cluster = gen_cluster(prototype=cluster_proto)
        action = gen_action(prototype=cluster_proto)
        action.state_on_success = "success"
        action.state_on_fail = "fail"
        action.multi_state_on_success_set = ["success"]
        action.multi_state_on_success_unset = ["success unset"]
        action.multi_state_on_fail_set = ["fail"]
        action.multi_state_on_fail_unset = ["fail unset"]
        action.save()
        task = gen_task_log(cluster, action)
        job = gen_job_log(task)
        job.sub_action = SubAction.objects.create(action=action, state_on_fail="sub_action fail")

        # status: expected state, expected multi_state set, expected multi_state unset
        test_data = [
            [JobStatus.SUCCESS, "success", ["success"], ["success unset"]],
            [JobStatus.FAILED, "sub_action fail", ["fail"], ["fail unset"]],
            [JobStatus.ABORTED, None, [], []],
        ]
        for status, exp_state, exp_m_state_set, exp_m_state_unset in test_data:
            state, m_state_set, m_state_unset = get_state(action, job, status)

            self.assertEqual(state, exp_state)
            self.assertListEqual(m_state_set, exp_m_state_set)
            self.assertListEqual(m_state_unset, exp_m_state_unset)

    def test_set_action_state(self):
        # pylint: disable=too-many-locals

        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        cluster = Cluster.objects.create(prototype=prototype)
        cluster_object = ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = Host.objects.create(prototype=prototype)
        host_provider = HostProvider.objects.create(prototype=prototype)
        adcm = ADCM.objects.create(prototype=prototype)
        action = Action.objects.create(prototype=prototype)
        task = TaskLog.objects.create(action=action, object_id=1, start_date=timezone.now(), finish_date=timezone.now())
        to_set = "to set"
        to_unset = "to unset"
        for obj in (adcm, cluster, cluster_object, host_provider, host):
            obj.set_multi_state(to_unset)

        data = [
            (cluster_object, "running", to_set, to_unset),
            (cluster, "removed", to_set, to_unset),
            (host, None, to_set, to_unset),
            (host_provider, "stopped", to_set, to_unset),
            (adcm, "initiated", to_set, to_unset),
        ]

        for obj, state, ms_to_set, ms_to_unset in data:
            with self.subTest(obj=obj, state=state):
                set_action_state(action, task, obj, state, [ms_to_set], [ms_to_unset])

            self.assertEqual(obj.state, state or "created")
            self.assertIn(to_set, obj.multi_state)
            self.assertNotIn(to_unset, obj.multi_state)

    @patch("cm.job.save_hc")
    def test_restore_hc(self, mock_save_hc):
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        cluster = Cluster.objects.create(prototype=prototype)
        cluster_object = ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = Host.objects.create(prototype=prototype, cluster=cluster)
        component = Prototype.objects.create(parent=prototype, type="component", bundle=bundle)
        service_component = ServiceComponent.objects.create(
            cluster=cluster, service=cluster_object, prototype=component
        )
        hostcomponentmap = [
            {
                "host_id": host.id,
                "service_id": cluster_object.id,
                "component_id": service_component.id,
            }
        ]
        action = Action.objects.create(prototype=prototype, hostcomponentmap=hostcomponentmap)
        task = TaskLog.objects.create(
            action=action,
            task_object=cluster,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            selector={"cluster": cluster.id},
            hostcomponentmap=hostcomponentmap,
        )

        restore_hc(task, action, JobStatus.FAILED)
        mock_save_hc.assert_called_once_with(cluster, [(cluster_object, host, service_component)])

    @patch("cm.job.raise_adcm_ex")
    def test_check_service_task(self, mock_err):
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        cluster = Cluster.objects.create(prototype=prototype)
        cluster_object = ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        action = Action.objects.create(prototype=prototype)

        service = check_service_task(cluster.id, action)

        self.assertEqual(cluster_object, service)
        self.assertEqual(mock_err.call_count, 0)

    @patch("cm.job.raise_adcm_ex")
    def test_check_cluster(self, mock_err):
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        cluster = Cluster.objects.create(prototype=prototype)

        test_cluster = check_cluster(cluster.id)

        self.assertEqual(cluster, test_cluster)
        self.assertEqual(mock_err.call_count, 0)

    @patch("cm.job.prepare_ansible_config")
    @patch("cm.job.prepare_job_config")
    @patch("cm.job.prepare_job_inventory")
    def test_prepare_job(self, mock_prepare_job_inventory, mock_prepare_job_config, mock_prepare_ansible_config):
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        cluster = Cluster.objects.create(prototype=prototype)
        action = Action.objects.create(prototype=prototype)
        job = JobLog.objects.create(action=action, start_date=timezone.now(), finish_date=timezone.now())

        prepare_job(action, None, job.id, cluster, "", {}, None, False)

        mock_prepare_job_inventory.assert_called_once_with(cluster, job.id, action, {}, None)
        mock_prepare_job_config.assert_called_once_with(action, None, job.id, cluster, "", False)
        mock_prepare_ansible_config.assert_called_once_with(job.id, action, None)

    @patch("cm.job.get_obj_config")
    def test_get_adcm_config(self, mock_get_obj_config):
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        adcm = ADCM.objects.create(prototype=prototype)
        mock_get_obj_config.return_value = {}

        conf = get_adcm_config()

        self.assertEqual(conf, {})
        mock_get_obj_config.assert_called_once_with(adcm)

    def test_prepare_context(self):
        bundle = Bundle.objects.create()
        proto1 = Prototype.objects.create(bundle=bundle, type="cluster")
        action1 = Action.objects.create(prototype=proto1)
        add_cluster(proto1, "Garbage")
        cluster = add_cluster(proto1, "Ontario")
        context = prepare_context(action1, cluster)

        self.assertDictEqual(context, {"type": "cluster", "cluster_id": cluster.id})

        proto2 = Prototype.objects.create(bundle=bundle, type="service")
        action2 = Action.objects.create(prototype=proto2)
        service = add_service_to_cluster(cluster, proto2)
        context = prepare_context(action2, service)

        self.assertDictEqual(context, {"type": "service", "service_id": service.id, "cluster_id": cluster.id})

    def test_get_bundle_root(self):
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        action = Action.objects.create(prototype=prototype)

        data = [("adcm", str(Path(settings.BASE_DIR, "conf"))), ("", str(settings.BUNDLE_DIR))]

        for prototype_type, test_path in data:
            prototype.type = prototype_type
            prototype.save()

            path = get_bundle_root(action)

            self.assertEqual(path, test_path)

    @patch("cm.job.get_bundle_root")
    def test_cook_script(self, mock_get_bundle_root):
        bundle = Bundle.objects.create(hash="6525d392dc9d1fb3273fb4244e393672579d75f3")
        prototype = Prototype.objects.create(bundle=bundle)
        action = Action.objects.create(prototype=prototype)
        sub_action = SubAction.objects.create(action=action, script="ansible/sleep.yaml")
        mock_get_bundle_root.return_value = str(settings.BUNDLE_DIR)

        data = [
            (
                sub_action,
                "main.yaml",
                str(Path(settings.BUNDLE_DIR, action.prototype.bundle.hash, "ansible/sleep.yaml")),
            ),
            (
                None,
                "main.yaml",
                str(Path(settings.BUNDLE_DIR, action.prototype.bundle.hash, "main.yaml")),
            ),
            (
                None,
                "./main.yaml",
                str(Path(settings.BUNDLE_DIR, action.prototype.bundle.hash, "main.yaml")),
            ),
        ]

        for data_sub_action, script, test_path in data:
            with self.subTest(sub_action=sub_action, script=script):
                action.script = script
                action.save()

                path = cook_script(action, data_sub_action)

            self.assertEqual(path, test_path)
            mock_get_bundle_root.assert_called_once_with(action)
            mock_get_bundle_root.reset_mock()

    @patch("cm.job.cook_script")
    @patch("cm.job.get_bundle_root")
    @patch("cm.job.prepare_context")
    @patch("cm.job.get_adcm_config")
    @patch("json.dump")
    @patch("builtins.open")
    def test_prepare_job_config(
        self,
        mock_open,
        mock_dump,
        mock_get_adcm_config,
        mock_prepare_context,
        mock_get_bundle_root,
        mock_cook_script,
    ):
        # pylint: disable=too-many-locals

        bundle = Bundle.objects.create()
        proto1 = Prototype.objects.create(bundle=bundle, type="cluster")
        cluster = Cluster.objects.create(prototype=proto1)
        proto2 = Prototype.objects.create(bundle=bundle, type="service", name="Hive")
        service = add_service_to_cluster(cluster, proto2)
        cluster_action = Action.objects.create(prototype=proto1)
        service_action = Action.objects.create(prototype=proto2)
        proto3 = Prototype.objects.create(bundle=bundle, type="adcm")
        adcm_action = Action.objects.create(prototype=proto3)
        adcm = ADCM.objects.create(prototype=proto3)

        file_mock = Mock()
        mock_open.return_value = file_mock
        mock_get_adcm_config.return_value = {}
        mock_prepare_context.return_value = {"type": "cluster", "cluster_id": 1}
        mock_get_bundle_root.return_value = str(settings.BUNDLE_DIR)
        mock_cook_script.return_value = str(
            Path(settings.BUNDLE_DIR, cluster_action.prototype.bundle.hash, cluster_action.script)
        )

        job = JobLog.objects.create(action=cluster_action, start_date=timezone.now(), finish_date=timezone.now())

        conf = "test"
        proto4 = Prototype.objects.create(bundle=bundle, type="provider")
        provider_action = Action.objects.create(prototype=proto4)
        provider = HostProvider(prototype=proto4)
        proto5 = Prototype.objects.create(bundle=bundle, type="host")
        host_action = Action.objects.create(prototype=proto5)
        host = Host(prototype=proto5, provider=provider)

        data = [
            ("service", service, service_action),
            ("cluster", cluster, cluster_action),
            ("host", host, host_action),
            ("provider", provider, provider_action),
            ("adcm", adcm, adcm_action),
        ]

        for prototype_type, obj, action in data:
            with self.subTest(provider_type=prototype_type, obj=obj):
                prepare_job_config(action, None, job.pk, obj, conf, False)

                job_config = {
                    "adcm": {"config": {}},
                    "context": {"type": "cluster", "cluster_id": 1},
                    "env": {
                        "run_dir": mock_dump.call_args[0][0]["env"]["run_dir"],
                        "log_dir": mock_dump.call_args[0][0]["env"]["log_dir"],
                        "tmp_dir": str(Path(settings.RUN_DIR, f"{job.id}", "tmp")),
                        "stack_dir": mock_dump.call_args[0][0]["env"]["stack_dir"],
                        "status_api_token": mock_dump.call_args[0][0]["env"]["status_api_token"],
                    },
                    "job": {
                        "id": job.pk,
                        "action": action.name,
                        "job_name": "",
                        "command": "",
                        "script": "",
                        "verbose": False,
                        "playbook": mock_dump.call_args[0][0]["job"]["playbook"],
                        "config": "test",
                    },
                }
                if prototype_type == "service":
                    job_config["job"].update(
                        {
                            "hostgroup": obj.prototype.name,
                            "service_id": obj.id,
                            "service_type_id": obj.prototype.id,
                            "cluster_id": cluster.id,
                        }
                    )

                elif prototype_type == "cluster":
                    job_config["job"]["cluster_id"] = cluster.id
                    job_config["job"]["hostgroup"] = "CLUSTER"
                elif prototype_type == "host":
                    job_config["job"].update(
                        {
                            "hostgroup": "HOST",
                            "hostname": obj.fqdn,
                            "host_id": obj.id,
                            "host_type_id": obj.prototype.id,
                            "provider_id": obj.provider.id,
                        }
                    )
                elif prototype_type == "provider":
                    job_config["job"].update({"hostgroup": "PROVIDER", "provider_id": obj.id})
                elif prototype_type == "adcm":
                    job_config["job"]["hostgroup"] = "127.0.0.1"

                mock_open.assert_called_with(
                    settings.RUN_DIR / f"{job.id}" / "config.json",
                    "w",
                    encoding=settings.ENCODING_UTF_8,
                )
                mock_dump.assert_called_with(job_config, file_mock, indent=3, sort_keys=True)
                mock_get_adcm_config.assert_called()
                mock_prepare_context.assert_called_with(action, obj)
                mock_get_bundle_root.assert_called_with(action)
                mock_cook_script.assert_called_with(action, None)

    @patch("cm.job.cook_delta")
    @patch("cm.job.get_old_hc")
    @patch("cm.job.get_actual_hc")
    @patch("cm.job.prepare_job")
    def test_re_prepare_job(self, mock_prepare_job, mock_get_actual_hc, mock_get_old_hc, mock_cook_delta):
        # pylint: disable=too-many-locals

        new_hc = Mock()
        mock_get_actual_hc.return_value = new_hc
        old_hc = Mock()
        mock_get_old_hc.return_value = old_hc
        delta = Mock()
        mock_cook_delta.return_value = delta

        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        cluster = Cluster.objects.create(prototype=prototype)
        cluster_object = ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = Host.objects.create(prototype=prototype, cluster=cluster)
        component = Prototype.objects.create(parent=prototype, type="component", bundle=bundle)
        service_component = ServiceComponent.objects.create(
            cluster=cluster, service=cluster_object, prototype=component
        )
        action = Action.objects.create(
            prototype=prototype, hostcomponentmap=[{"service": "", "component": "", "action": ""}]
        )
        sub_action = SubAction.objects.create(action=action)
        hostcomponentmap = [
            {
                "host_id": host.id,
                "service_id": cluster_object.id,
                "component_id": service_component.id,
            }
        ]
        task = TaskLog.objects.create(
            action=action,
            task_object=cluster,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            hostcomponentmap=hostcomponentmap,
            config={"sleeptime": 1},
        )
        job = JobLog.objects.create(
            task=task,
            action=action,
            sub_action=sub_action,
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )

        re_prepare_job(task, job)

        mock_get_actual_hc.assert_called_once_with(cluster)
        mock_get_old_hc.assert_called_once_with(task.hostcomponentmap)
        mock_cook_delta.assert_called_once_with(cluster, new_hc, action.hostcomponentmap, old_hc)
        mock_prepare_job.assert_called_once_with(action, sub_action, job.id, cluster, task.config, delta, None, False)

    def test_job_termination_allowed_action_termination_allowed(self):
        self.init_adcm()
        self.login()
        action_name = "action_termination_allowed"
        job_display_name = "subaction_termination_allowed"

        response = self.create_multijob_cluster()
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response, action = self.get_cluster_action(cluster_id=response.json()["id"], action_name=action_name)
        self.assertEqual(response.status_code, HTTP_200_OK)
        if action is None:
            raise AssertionError(f"Can't find '{action_name}' action in cluster '{self.multijob_cluster_name}'")

        with patch("cm.job.run_task"):
            response, job = self.run_action_get_target_job(
                action=action, job_display_name=job_display_name, force_job_status=JobStatus.RUNNING
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'"
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse("joblog-cancel", kwargs={"job_pk": job["id"]}), content_type=APPLICATION_JSON
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        kill_mock.assert_called_once_with(self.job_fake_pid, SIGTERM)

    def test_job_termination_disallowed_action_termination_allowed(self):
        self.init_adcm()
        self.login()
        action_name = "action_termination_allowed"
        job_display_name = "subaction_termination_disallowed"

        response = self.create_multijob_cluster()
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response, action = self.get_cluster_action(cluster_id=response.json()["id"], action_name=action_name)
        self.assertEqual(response.status_code, HTTP_200_OK)
        if action is None:
            raise AssertionError(f"Can't find '{action_name}' action in cluster '{self.multijob_cluster_name}'")

        with patch("cm.job.run_task"):
            response, job = self.run_action_get_target_job(
                action=action, job_display_name=job_display_name, force_job_status=JobStatus.RUNNING
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'"
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse("joblog-cancel", kwargs={"job_pk": job["id"]}), content_type=APPLICATION_JSON
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        kill_mock.assert_not_called()

    def test_job_termination_not_defined_action_termination_allowed(self):
        self.init_adcm()
        self.login()
        action_name = "action_termination_allowed"
        job_display_name = "subaction_termination_not_defined"

        response = self.create_multijob_cluster()
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response, action = self.get_cluster_action(cluster_id=response.json()["id"], action_name=action_name)
        self.assertEqual(response.status_code, HTTP_200_OK)
        if action is None:
            raise AssertionError(f"Can't find '{action_name}' action in cluster '{self.multijob_cluster_name}'")

        with patch("cm.job.run_task"):
            response, job = self.run_action_get_target_job(
                action=action, job_display_name=job_display_name, force_job_status=JobStatus.RUNNING
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'"
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse("joblog-cancel", kwargs={"job_pk": job["id"]}), content_type=APPLICATION_JSON
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        kill_mock.assert_called_once_with(self.job_fake_pid, SIGTERM)

    def test_job_termination_allowed_action_termination_not_allowed(self):
        self.init_adcm()
        self.login()
        action_name = "action_termination_not_allowed"
        job_display_name = "subaction_termination_allowed"

        response = self.create_multijob_cluster()
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response, action = self.get_cluster_action(cluster_id=response.json()["id"], action_name=action_name)
        self.assertEqual(response.status_code, HTTP_200_OK)
        if action is None:
            raise AssertionError(f"Can't find '{action_name}' action in cluster '{self.multijob_cluster_name}'")

        with patch("cm.job.run_task"):
            response, job = self.run_action_get_target_job(
                action=action, job_display_name=job_display_name, force_job_status=JobStatus.RUNNING
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'"
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse("joblog-cancel", kwargs={"job_pk": job["id"]}), content_type=APPLICATION_JSON
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        kill_mock.assert_called_once_with(self.job_fake_pid, SIGTERM)

    def test_job_termination_disallowed_action_termination_not_allowed(self):
        self.init_adcm()
        self.login()
        action_name = "action_termination_not_allowed"
        job_display_name = "subaction_termination_disallowed"

        response = self.create_multijob_cluster()
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response, action = self.get_cluster_action(cluster_id=response.json()["id"], action_name=action_name)
        self.assertEqual(response.status_code, HTTP_200_OK)
        if action is None:
            raise AssertionError(f"Can't find '{action_name}' action in cluster '{self.multijob_cluster_name}'")

        with patch("cm.job.run_task"):
            response, job = self.run_action_get_target_job(
                action=action, job_display_name=job_display_name, force_job_status=JobStatus.RUNNING
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'"
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse("joblog-cancel", kwargs={"job_pk": job["id"]}), content_type=APPLICATION_JSON
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        kill_mock.assert_not_called()

    def test_job_termination_not_defined_action_termination_not_allowed(self):
        self.init_adcm()
        self.login()
        action_name = "action_termination_not_allowed"
        job_display_name = "subaction_termination_not_defined"

        response = self.create_multijob_cluster()
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response, action = self.get_cluster_action(cluster_id=response.json()["id"], action_name=action_name)
        self.assertEqual(response.status_code, HTTP_200_OK)
        if action is None:
            raise AssertionError(f"Can't find '{action_name}' action in cluster '{self.multijob_cluster_name}'")

        with patch("cm.job.run_task"):
            response, job = self.run_action_get_target_job(
                action=action, job_display_name=job_display_name, force_job_status=JobStatus.RUNNING
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'"
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse("joblog-cancel", kwargs={"job_pk": job["id"]}), content_type=APPLICATION_JSON
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        kill_mock.assert_not_called()

    def test_job_termination_not_allowed_if_job_not_in_running_status(self):
        self.init_adcm()
        self.login()
        action_name = "action_termination_allowed"
        job_display_name = "subaction_termination_not_defined"

        response = self.create_multijob_cluster()
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response, action = self.get_cluster_action(cluster_id=response.json()["id"], action_name=action_name)
        self.assertEqual(response.status_code, HTTP_200_OK)
        if action is None:
            raise AssertionError(f"Can't find '{action_name}' action in cluster '{self.multijob_cluster_name}'")

        with patch("cm.job.run_task"):
            response, job = self.run_action_get_target_job(
                action=action,
                job_display_name=job_display_name,
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'"
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse("joblog-cancel", kwargs={"job_pk": job["id"]}), content_type=APPLICATION_JSON
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        kill_mock.assert_not_called()

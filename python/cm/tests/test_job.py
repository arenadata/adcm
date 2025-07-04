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
from unittest.mock import patch
from urllib.parse import urljoin

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from django.conf import settings
from django.urls import reverse
from init_db import init
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT

from cm.models import (
    Action,
    Bundle,
    JobLog,
    JobStatus,
    Prototype,
)


def get_bundle_root(action: Action) -> str:
    if action.prototype.type == "adcm":
        return str(Path(settings.BASE_DIR, "conf"))

    return str(settings.BUNDLE_DIR)


class TestJob(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None  # pylint: disable=invalid-name
        self.test_files_dir = self.base_dir / "python" / "cm" / "tests" / "files"
        self.multijob_bundle = "multijob_cluster.tar"
        self.multijob_cluster_name = "multijob_cluster"
        self.test_user_username = "admin"
        self.test_user_password = "admin"
        self.job_fake_pid = 9999

    # some tests do not need client / manually create `ADCM` object
    @staticmethod
    def init_adcm():
        init()

    def create_multijob_cluster(self) -> Response:
        bundle_id = self.upload_and_load_bundle(path=Path(self.test_files_dir, self.multijob_bundle)).pk

        return self.client.post(
            path=reverse(viewname="v1:cluster"),
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
            path=reverse(viewname="v1:object-action", kwargs={"cluster_id": cluster_id, "object_type": "cluster"}),
            content_type=APPLICATION_JSON,
        )

        target_action = None
        for action in response.json():
            if action["name"] == action_name:
                target_action = action
                break

        return response, target_action

    def run_action_get_target_job(
        self,
        action: dict,
        job_display_name: str,
        force_job_status: JobStatus | None = None,
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

        with patch("cm.services.job.run.start_task"):
            response, job = self.run_action_get_target_job(
                action=action,
                job_display_name=job_display_name,
                force_job_status=JobStatus.RUNNING,
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'",
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse(viewname="v1:joblog-cancel", kwargs={"job_pk": job["id"]}),
                content_type=APPLICATION_JSON,
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

        with patch("cm.services.job.run.start_task"):
            response, job = self.run_action_get_target_job(
                action=action,
                job_display_name=job_display_name,
                force_job_status=JobStatus.RUNNING,
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'",
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse(viewname="v1:joblog-cancel", kwargs={"job_pk": job["id"]}),
                content_type=APPLICATION_JSON,
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

        with patch("cm.services.job.run.start_task"):
            response, job = self.run_action_get_target_job(
                action=action,
                job_display_name=job_display_name,
                force_job_status=JobStatus.RUNNING,
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'",
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse(viewname="v1:joblog-cancel", kwargs={"job_pk": job["id"]}),
                content_type=APPLICATION_JSON,
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

        with patch("cm.services.job.run.start_task"):
            response, job = self.run_action_get_target_job(
                action=action,
                job_display_name=job_display_name,
                force_job_status=JobStatus.RUNNING,
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'",
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse(viewname="v1:joblog-cancel", kwargs={"job_pk": job["id"]}),
                content_type=APPLICATION_JSON,
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

        with patch("cm.services.job.run.start_task"):
            response, job = self.run_action_get_target_job(
                action=action,
                job_display_name=job_display_name,
                force_job_status=JobStatus.RUNNING,
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'",
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse(viewname="v1:joblog-cancel", kwargs={"job_pk": job["id"]}),
                content_type=APPLICATION_JSON,
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

        with patch("cm.services.job.run.start_task"):
            response, job = self.run_action_get_target_job(
                action=action,
                job_display_name=job_display_name,
                force_job_status=JobStatus.RUNNING,
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'",
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse(viewname="v1:joblog-cancel", kwargs={"job_pk": job["id"]}),
                content_type=APPLICATION_JSON,
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

        with patch("cm.services.job.run.start_task"):
            response, job = self.run_action_get_target_job(
                action=action,
                job_display_name=job_display_name,
            )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        if job is None:
            raise AssertionError(
                f"Can't find job '{job_display_name}' "
                f"in action '{action_name}' of cluster '{self.multijob_cluster_name}'",
            )

        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.put(
                path=reverse(viewname="v1:joblog-cancel", kwargs={"job_pk": job["id"]}),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        kill_mock.assert_not_called()

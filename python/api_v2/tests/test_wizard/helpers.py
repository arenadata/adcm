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
from typing import Any, Collection

from cm.converters import orm_object_to_core_descriptor
from cm.legacy.issue import add_concern_to_object
from cm.legacy.services.action_process.schema_validation import ProcessOperationType
from cm.legacy.services.action_process.types import ProcessStepState
from cm.legacy.services.concern import create_issue
from cm.models import (
    Action,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    HostComponent,
    Process,
    ProcessStep,
    ProcessStepInput,
    Service,
)
from core.types import CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from jinja2 import Template
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
import yaml


def render_template(file: Path, context: dict) -> Any:
    data = Template(source=file.read_text(encoding="utf-8")).render(**context)
    return yaml.safe_load(data)


class WizardProcessHelpers:
    def submit_config_step(
        self,
        owner: Cluster,
        action: Action | int,
        process: Process,
        step_id: int,
        config_payload: dict,
        *,
        expected_status: int = HTTP_200_OK,
    ) -> Response:
        process.refresh_from_db()
        data = {
            "method": ProcessOperationType.SUBMIT,
            "params": {
                "processSyncKey": process.sync_key,
                "stepId": step_id,
                "configuration": {
                    "config": config_payload["config"],
                    "adcmMeta": config_payload.get("adcmMeta", {}),
                },
            },
        }

        return self.submit_step_r(
            owner=owner, action=action, process_id=process.id, data=data, expected_status=expected_status
        )

    def make_step_current(self, step: ProcessStep) -> None:
        steps_qs = ProcessStep.objects.filter(process_id=step.process_id)
        steps_qs.filter(id__lt=step.id).update(state=ProcessStepState.COMPLETED)

        self_and_next_ids = set(steps_qs.filter(id__gte=step.id).values_list("id", flat=True))
        steps_qs.filter(id__in=self_and_next_ids).update(state=ProcessStepState.CREATED)
        ProcessStepInput.objects.filter(step_id__in=self_and_next_ids).delete()

    def get_object_action_with_process(self, obj: Cluster | Service | Component):
        return Action.objects.get(name="wizard_jinja", prototype=obj.prototype)

    @staticmethod
    def set_completed_fill_specs_create_inputs_for_steps_by_name(process_id: int, step_names: Collection[str]) -> None:
        # Fill previous steps' `step_spec`, create inputs for them, set `completed` state
        for step in ProcessStep.objects.filter(process_id=process_id, name__in=step_names):
            step.step_spec = [{"name": "a", "subname": ""}]
            step.state = ProcessStepState.COMPLETED
            step.save(update_fields=["step_spec", "state"])
            ProcessStepInput.objects.create(step_id=step.id, job=None, configuration={"config": {}, "attr": {}})

    def cleanup_process_hc_service(self, cluster_id: int, service_ids: list[int], process_id: int):
        HostComponent.objects.filter(cluster_id=cluster_id).delete()
        for service in Service.objects.filter(cluster_id=cluster_id, id__in=service_ids):
            response = self.client.v2[service].delete()
            self.assertEqual(response.status_code, 204)
        steps_qs = ProcessStep.objects.filter(process_id=process_id)
        ProcessStepInput.objects.filter(step_id__in=steps_qs.values_list("id", flat=True)).delete()
        steps_qs.delete()
        Process.objects.get(id=process_id).delete()

    def advance_two_config_steps(self, process: Process, owner: Cluster, action: Action | int):
        config_payload = {"config": {"integer_field": 10, "string_field": "string"}, "adcmMeta": {}}
        self.submit_config_step(
            owner=owner, action=action, process=process, step_id=process.current_step_id, config_payload=config_payload
        )

        process.refresh_from_db()

        config_payload = {"config": {"int": 10}, "adcmMeta": {}}
        self.submit_config_step(
            owner=owner, action=action, process=process, step_id=process.current_step_id, config_payload=config_payload
        )

    def clear_hostcomponent_mapping(self, cluster_id: int) -> None:
        HostComponent.objects.filter(cluster_id=cluster_id).delete()

    def add_issue_and_concern_to_object(self, object_, cause: ConcernCause):
        issue = create_issue(
            owner=CoreObjectDescriptor(id=object_.id, type=orm_object_to_core_descriptor(object_).type),
            cause=cause,
        )
        add_concern_to_object(object_=object_, concern=issue)
        return issue

    def delete_concern_by_name(self, object_, name: str) -> None:
        ConcernItem.objects.filter(
            name=name, owner_id=object_.id, owner_type=ContentType.objects.get_for_model(object_)
        ).delete()

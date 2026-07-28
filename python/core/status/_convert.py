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

from core.status._types import EntityStatus, MonitoringType, RawStatus


def convert_to_entity_status(raw_status: RawStatus | None) -> EntityStatus:
    return EntityStatus.UP if raw_status == 0 else EntityStatus.DOWN


def convert_to_service_status(raw_status: RawStatus | None, monitoring: MonitoringType) -> EntityStatus:
    return _convert_to_status_considering_monitoring(raw_status=raw_status, monitoring=monitoring)


def convert_to_component_status(raw_status: RawStatus | None, monitoring: MonitoringType) -> EntityStatus:
    return _convert_to_status_considering_monitoring(raw_status=raw_status, monitoring=monitoring)


def convert_to_host_component_status(
    raw_status: RawStatus | None, component_monitoring: MonitoringType
) -> EntityStatus:
    return _convert_to_status_considering_monitoring(raw_status=raw_status, monitoring=component_monitoring)


def _convert_to_status_considering_monitoring(raw_status: RawStatus | None, monitoring: MonitoringType) -> EntityStatus:
    if monitoring == "passive":
        return EntityStatus.UP

    return convert_to_entity_status(raw_status=raw_status)

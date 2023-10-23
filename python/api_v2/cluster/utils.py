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

from api_v2.prototype.utils import get_license_text
from cm.models import ObjectType, Prototype


def get_depend_on(
    prototype: Prototype, depend_on: list[dict] | None = None, checked_objects: list[Prototype] | None = None
) -> list[dict]:
    if depend_on is None:
        depend_on = []

    if checked_objects is None:
        checked_objects = []

    checked_objects.append(prototype)

    for require in prototype.requires:
        required_service = Prototype.objects.get(
            type=ObjectType.SERVICE, name=require["service"], bundle=prototype.bundle
        )
        service_prototype = {
            "id": required_service.pk,
            "name": required_service.name,
            "display_name": required_service.display_name,
            "version": required_service.version,
            "license": {"status": required_service.license, "text": get_license_text(prototype=required_service)},
            "component_prototypes": [],
        }

        required_component = None

        if "component" in require:
            required_component = Prototype.objects.get(
                type=ObjectType.COMPONENT, name=require["component"], bundle=prototype.bundle, parent=required_service
            )
            service_prototype["component_prototypes"].append(
                {
                    "id": required_component.pk,
                    "name": required_component.name,
                    "display_name": required_component.display_name,
                    "version": required_component.version,
                }
            )

        depend_on.append(service_prototype)

        if required_service.requires and required_service not in checked_objects:
            get_depend_on(prototype=required_service, depend_on=depend_on, checked_objects=checked_objects)

        if required_component and required_component.requires and required_component not in checked_objects:
            get_depend_on(prototype=required_component, depend_on=depend_on, checked_objects=checked_objects)

    return depend_on

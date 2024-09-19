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

from collections import defaultdict

from cm.models import ObjectType, Prototype

from api_v2.prototype.utils import get_license_text


def get_requires(requires: list[dict]) -> dict:
    new_requires = defaultdict(list)

    for require in requires:
        if "component" in require:
            new_requires[require["service"]].append(require["component"])
        elif require["service"] not in new_requires:
            new_requires[require["service"]] = []

    return new_requires


def get_depend_on(
    prototype: Prototype, depend_on: list[dict] | None = None, checked_objects: set[Prototype] | None = None
) -> list[dict]:
    if depend_on is None:
        depend_on = []

    if checked_objects is None:
        checked_objects = set()

    checked_objects.add(prototype)

    for service_name, component_names in get_requires(requires=prototype.requires).items():
        required_service = Prototype.objects.get(type=ObjectType.SERVICE, name=service_name, bundle=prototype.bundle)
        checked_objects.add(required_service)
        service_prototype = {
            "id": required_service.pk,
            "name": required_service.name,
            "display_name": required_service.display_name,
            "version": required_service.version,
            "license": {
                "status": required_service.license,
                "text": get_license_text(
                    license_path=required_service.license_path,
                    bundle_hash=required_service.bundle.hash,
                ),
            },
            "component_prototypes": [],
        }

        for component_name in component_names:
            required_component = Prototype.objects.get(
                type=ObjectType.COMPONENT, name=component_name, bundle=prototype.bundle, parent=required_service
            )
            checked_objects.add(required_component)
            service_prototype["component_prototypes"].append(
                {
                    "id": required_component.pk,
                    "name": required_component.name,
                    "display_name": required_component.display_name,
                    "version": required_component.version,
                }
            )

            if required_component.requires and required_component not in checked_objects:
                get_depend_on(prototype=required_component, depend_on=depend_on, checked_objects=checked_objects)

        depend_on.append({"service_prototype": service_prototype})

        if required_service.requires and required_service not in checked_objects:
            get_depend_on(prototype=required_service, depend_on=depend_on, checked_objects=checked_objects)

    return depend_on

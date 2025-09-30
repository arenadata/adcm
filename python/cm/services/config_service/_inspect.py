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

from core import config
from core import result as r

from cm import converters
from cm.models import MainObject
from cm.services.config_service import retrieve
from cm.services.config_service._validators import AlwaysPassValidator


# Not much put into design of this.
# It's unclear for now on which level should this one exist,
# but for now it's made compliant with existing interface, expected by concerns recheck machinery.
def has_issue(target: MainObject) -> bool:
    # Calling config service for objects without configuration is not designed for now,
    # so have to check explicitly like that.
    # Better be reworked.
    if not target.config:
        return False

    owner = converters.orm_object_to_core_descriptor(target)
    specification, _ = retrieve.get_specification(owner=owner)
    configuration = retrieve.get_current_configuration(owner=target)
    flat_configuration = config.nested_to_flat(configuration=configuration, specification=specification)

    # for issues we sort of rely on defaults validation,
    # so aren't interested in variant/pattern violations
    # => may as well skip them
    always_pass_validator = AlwaysPassValidator()

    result = config.operations.validate_values(
        configuration=flat_configuration,
        specification=specification,
        validators=config.Validators(variant=always_pass_validator, pattern=always_pass_validator),
        check_inside_deactivated_groups=False,
    )

    return r.is_fail(result)

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

from core import bundle, config

from cm.impl.bundle.repo import convert_config_definition_to_orm_model
from cm.impl.common.config_spec import build_defaults, build_specification


def definition_to_full_spec(
    definition: bundle.d.ConfigDefinition,
    bundle_root: Path,
    secrets: config.secrets.AnsibleSecrets,
) -> tuple[config.spec.FullSpec, config.Defaults]:
    records = tuple(convert_config_definition_to_orm_model(definition, prototype=None, action=None))
    specification = build_specification(
        records=records,
        # can't detect customization flag in here and it's not important for validation
        group_customization_flag=False,
    )
    defaults = build_defaults(records=records, spec=specification, bundle_root=bundle_root, encrypt=secrets.encrypt)

    return specification, defaults

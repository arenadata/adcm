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

"""
Package defines Configuration Specification and types for Parameters used in it.
Should be used via its public API only, no import from `spec` allowed from outside modules.
Parameters are accessible via `p` (e.g. `spec.p.SimpleParameter`)
"""

from core.config._spec import parameters as p
from core.config._spec.jsonschema import spec_to_jsonschema
from core.config._spec.operations import StatefulParameters, detect_deactivated_parameters, detect_stateful_parameters
from core.config._spec.spec import FullSpec, SpecAttributes, SpecHierarchyLevel

__all__ = [
    "FullSpec",
    "SpecAttributes",
    "SpecHierarchyLevel",
    "StatefulParameters",
    "detect_deactivated_parameters",
    "detect_stateful_parameters",
    "p",
    "spec_to_jsonschema",
]

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

from typing import Final

from core.bundle._parsing.v_2_0.base_parser import BaseParser as ParserV2
from core.bundle._parsing.v_2_1.targets import (
    ADCMSchema,
    Cluster,
    Host,
    Provider,
    RootTarget,
    Service,
)

TYPE_SCHEMA_MAP: Final[dict[str, type[RootTarget]]] = {
    "cluster": Cluster,
    "service": Service,
    "provider": Provider,
    "host": Host,
    "adcm": ADCMSchema,
}


class Parser(ParserV2):
    def _get_schema_mapping(self) -> dict[str, type[RootTarget]]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return TYPE_SCHEMA_MAP

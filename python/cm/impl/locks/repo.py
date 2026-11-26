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

from dataclasses import dataclass
from typing import Final

from core.locks import LockRepoI
from core.types import ADCMCoreType, Descriptor
from django.db import connection

_TYPE_CODE_MAP: Final = {
    ADCMCoreType.ADCM: "10",
    ADCMCoreType.PROVIDER: "11",
    ADCMCoreType.HOST: "12",
    ADCMCoreType.CLUSTER: "13",
    ADCMCoreType.SERVICE: "14",
    ADCMCoreType.COMPONENT: "15",
}

_SHARED_ASPECT_CODES: Final = {
    "config": "001",
    "state": "010",
    "multi_state": "011",
}

_TYPE_ASPECT_MAP: Final = {
    ADCMCoreType.ADCM: _SHARED_ASPECT_CODES,
    ADCMCoreType.PROVIDER: _SHARED_ASPECT_CODES,
    ADCMCoreType.HOST: _SHARED_ASPECT_CODES,
    ADCMCoreType.CLUSTER: {
        **_SHARED_ASPECT_CODES,
        "mapping": "002",
    },
    ADCMCoreType.SERVICE: _SHARED_ASPECT_CODES,
    ADCMCoreType.COMPONENT: _SHARED_ASPECT_CODES,
}


def pg_advisory_xact_lock(namespace: int, key: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", [namespace, key])


@dataclass(slots=True)
class LockRepo(LockRepoI):
    def register_lock_on_object_waiting(self, target: Descriptor, *, aspect: str | None = None) -> None:
        if not connection.in_atomic_block:
            message = "Lock on object can be registered only inside a transaction"
            raise RuntimeError(message)

        try:
            type_code = _TYPE_CODE_MAP[target.type]
        except KeyError as e:
            raise RuntimeError(f'Lock can\'t be performed on type "{target.type}"') from e

        aspect_code = "000"
        if aspect is not None:
            try:
                aspect_code = _TYPE_ASPECT_MAP[target.type][aspect]
            except KeyError as e:
                raise RuntimeError(f'Lock can\'t be peformed on aspect "{aspect}" for type "{target.type}"') from e

        namespace_code = f"4{type_code}{aspect_code}"

        # No integer (postgres) overflow check: object ids are expected to fit into integer key of pg_advisory_xact_lock
        pg_advisory_xact_lock(namespace=int(namespace_code), key=target.id)

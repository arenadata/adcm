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
from core.types import ADCMCoreType, ClusterDesc
from django.db import connection

_LOCK_NAMESPACES: Final[dict[ADCMCoreType, int]] = {ADCMCoreType.CLUSTER: 44100}


def pg_advisory_xact_lock(namespace: int, key: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", [namespace, key])


@dataclass(slots=True)
class LockRepo(LockRepoI):
    def register_lock_on_object_waiting(self, target: ClusterDesc) -> None:
        if not connection.in_atomic_block:
            message = "Lock on object can be registered only inside a transaction"
            raise RuntimeError(message)

        namespace = _LOCK_NAMESPACES[target.type]
        # No integer (postgres) overflow check: object ids are expected to fit into integer key of pg_advisory_xact_lock
        pg_advisory_xact_lock(namespace=namespace, key=target.id)

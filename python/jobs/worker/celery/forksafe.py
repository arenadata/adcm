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
Fork safety for database connections in the prefork pool.

Neither psycopg connections nor SQLAlchemy engines are fork-safe: anything the
worker parent has open when billiard forks a pool child is inherited by both,
and two processes speaking through one socket interleave protocol replies
(surfacing as errors like "the last operation didn't produce records (command
status: COMMIT)"). Celery's built-in Django fixup covers only Django-project
setups; this worker assembles its own app, so the same guarantees are made
explicitly here.

Call `install()` during app assembly to register the signal handlers.
"""

from celery.signals import worker_before_create_process, worker_process_init
from django.db import connections

from jobs.worker.celery.pg.transport import discard_engines_inherited_from_fork


def close_parent_connections_before_fork(**_) -> None:
    # In the parent, right before every pool fork (including replacement
    # children forked at runtime): bootstrap code and startup hooks use the ORM,
    # so a connection may be open. Close it so the child inherits no socket.
    # The parent's SQLAlchemy transport engine stays untouched: it is in active
    # use by the consumer, and the child discards its inherited copy instead.
    connections.close_all()


def close_inherited_connections_in_child(**_) -> None:
    # In each pool child, right after fork: drop everything inherited so the
    # child lazily opens connections of its own. Replacement children fork
    # after the parent's consumer has opened the transport, so the SQLAlchemy
    # engine cache is populated at fork time — and children publish to the
    # broker (chain links), so a stale cache would reuse the parent's sockets.
    connections.close_all()
    discard_engines_inherited_from_fork()


def install() -> None:
    # dispatch deduplicates receivers, so repeated installation is harmless
    worker_before_create_process.connect(close_parent_connections_before_fork)
    worker_process_init.connect(close_inherited_connections_in_child)

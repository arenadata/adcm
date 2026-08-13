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
PostgreSQL kombu transport for ADCM's Celery workers.

Unlike kombu's built-in ``sqla+postgresql`` transport this one:

* declares **fanout** support, so the standard Celery pidbox (``revoke``,
  ``ping``, ``rate_limit``, ...) works natively and the Consul-based control
  transport (``ConsulListenerStep`` / ``ConsulControl``) is no longer needed;
* drives fanout via PostgreSQL ``LISTEN``/``NOTIFY`` instead of table polling,
  and hooks the notify socket into kombu's async event loop so control commands
  are delivered without a 1s poll delay.

Durable task delivery still lives in SQL tables (see :mod:`.models`); only the
wakeup/broadcast path uses ``LISTEN``/``NOTIFY``.

Register it by pointing ``broker_url`` at the fully-qualified transport class::

    broker_url = "integrations.celery.pg.transport:Transport+postgresql+psycopg://..."
"""

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
WSGI config for adcm project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "adcm.settings")

application = get_wsgi_application()

# Register ADCM in Consul once the WSGI app (and thus Django) is initialized.
from api_v2.utils.di import prepare_container
from application.startup.consul import register_adcm_in_service_discovery_when_consul_configured  # noqa: E402

container = prepare_container()
register_adcm_in_service_discovery_when_consul_configured(container)

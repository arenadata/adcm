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

from adcm.dependencies import prepare_container
from django.core.management import BaseCommand, CommandError

from application.check import check_adcm_start_is_allowed


class Command(BaseCommand):
    help = """
    Verify if a specific migration has been applied, ensuring installed bundles
    compatibility before allowing upgrade to current version.
    """

    def handle(self, *_, **_kw):
        container = prepare_container()
        check_adcm_start_is_allowed(
            container=container,
            failure_exc=CommandError,
            report_message=lambda message: self.stdout.write(self.style.SUCCESS(message)),
            report_warning=lambda message: self.stderr.write(self.style.WARNING(message)),
        )

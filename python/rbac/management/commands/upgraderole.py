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

"""UpgradeRole command for Django manage.py"""

from cm.errors import AdcmEx
from django.core.management.base import BaseCommand, CommandError
from rbac.upgrade.role import init_roles


class Command(BaseCommand):
    """
    Command for upgrade roles

    Example:
        manage.py upgraderole
    """

    help = "Upgrade roles"

    def handle(self, *args, **options):
        """Handler method"""
        try:
            msg = init_roles()
            self.stdout.write(self.style.SUCCESS(msg))
        except AdcmEx as e:
            raise CommandError(e.msg) from None

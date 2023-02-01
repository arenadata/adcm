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

from django.db import migrations


def make_all_superusers(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    User.objects.all().update(is_superuser=True)


class Migration(migrations.Migration):
    dependencies = [
        ('cm', '0053_auto_20200415_1247'),
    ]

    operations = [
        migrations.RunPython(make_all_superusers),
    ]

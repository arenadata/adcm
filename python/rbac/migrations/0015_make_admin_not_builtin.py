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

# Generated by Django 3.2.19 on 2024-05-14 09:57

from django.db import migrations


def update_admin_user(apps, schema_editor):
    User = apps.get_model("rbac", "User")
    User.objects.filter(username="admin").update(built_in=False)


class Migration(migrations.Migration):
    dependencies = [
        ("rbac", "0014_alter_group_description"),
    ]

    operations = [
        migrations.RunPython(update_admin_user),
    ]
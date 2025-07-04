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

# Generated by Django 5.1.1 on 2025-05-28 15:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cm", "0138_extend_job_statuses_for_scheduler"),
    ]

    operations = [
        migrations.AddField(
            model_name="tasklog",
            name="executor",
            field=models.JSONField(default=dict),
        ),
    ]

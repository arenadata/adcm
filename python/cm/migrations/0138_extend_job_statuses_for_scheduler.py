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

# Generated by Django 5.1.1 on 2025-05-20 14:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cm", "0137_remove_tasklog_restore_hc_on_fail"),
    ]

    operations = [
        migrations.AlterField(
            model_name="joblog",
            name="status",
            field=models.CharField(
                choices=[
                    ("revoked", "revoked"),
                    ("created", "created"),
                    ("scheduled", "scheduled"),
                    ("queued", "queued"),
                    ("success", "success"),
                    ("failed", "failed"),
                    ("running", "running"),
                    ("locked", "locked"),
                    ("aborted", "aborted"),
                    ("broken", "broken"),
                ],
                default="created",
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name="tasklog",
            name="status",
            field=models.CharField(
                choices=[
                    ("revoked", "revoked"),
                    ("created", "created"),
                    ("scheduled", "scheduled"),
                    ("queued", "queued"),
                    ("success", "success"),
                    ("failed", "failed"),
                    ("running", "running"),
                    ("locked", "locked"),
                    ("aborted", "aborted"),
                    ("broken", "broken"),
                ],
                max_length=1000,
            ),
        ),
    ]

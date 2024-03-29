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

# Generated by Django 3.2.19 on 2023-10-25 18:23

from django.db import migrations, models
from django.utils import timezone


def fix_start_finish_date(apps, schema_editor):
    TaskLog = apps.get_model("cm", "TaskLog")
    JobLog = apps.get_model("cm", "JobLog")

    TaskLog.objects.filter(status="created").update(start_date=None, finish_date=None)
    JobLog.objects.filter(status="created").update(start_date=None, finish_date=None)


def revert_start_finish_date(apps, schema_editor):
    TaskLog = apps.get_model("cm", "TaskLog")
    JobLog = apps.get_model("cm", "JobLog")

    TaskLog.objects.filter(status="created").update(start_date=timezone.now(), finish_date=timezone.now())
    JobLog.objects.filter(status="created").update(start_date=timezone.now(), finish_date=timezone.now())


class Migration(migrations.Migration):
    dependencies = [
        ("cm", "0114_adcm_uuid"),
    ]

    operations = [
        migrations.AlterField(
            model_name="joblog",
            name="finish_date",
            field=models.DateTimeField(db_index=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name="joblog",
            name="start_date",
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name="tasklog",
            name="finish_date",
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name="tasklog",
            name="start_date",
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.RunPython(code=fix_start_finish_date, reverse_code=revert_start_finish_date),
    ]

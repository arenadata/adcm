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

# Generated by Django 3.2 on 2021-10-27 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cm', '0079_concernitem_cause'),
    ]

    operations = [
        migrations.AddField(
            model_name='stagesubaction',
            name='multi_state_on_fail_set',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='stagesubaction',
            name='multi_state_on_fail_unset',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='subaction',
            name='multi_state_on_fail_set',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='subaction',
            name='multi_state_on_fail_unset',
            field=models.JSONField(default=list),
        ),
    ]

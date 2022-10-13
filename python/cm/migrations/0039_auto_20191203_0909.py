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
# Generated by Django 2.2.6 on 2019-12-03 09:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cm', '0038_auto_20191119_1200'),
    ]

    operations = [
        migrations.AddField(
            model_name='prototype',
            name='path',
            field=models.CharField(default='', max_length=160),
        ),
        migrations.AddField(
            model_name='stageprototype',
            name='path',
            field=models.CharField(default='', max_length=160),
        ),
    ]

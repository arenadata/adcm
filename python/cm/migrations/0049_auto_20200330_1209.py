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

# Generated by Django 3.0.3 on 2020-03-30 12:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cm', '0048_auto_20200228_1032'),
    ]

    operations = [
        migrations.AlterField(
            model_name='joblog', name='finish_date', field=models.DateTimeField(db_index=True),
        ),
    ]

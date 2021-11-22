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
# Generated by Django 3.2.6 on 2021-11-22 10:48

from django.db import migrations, models

import rbac.models


class Migration(migrations.Migration):
    dependencies = [
        ('rbac', '0002_copy_profile'),
    ]

    operations = [
        migrations.RenameField(
            model_name='role',
            old_name='childs',
            new_name='child',
        ),
        migrations.AddField(
            model_name='role',
            name='built_in',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='role',
            name='category',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='role',
            name='parametrized_by_type',
            field=models.JSONField(default=list, validators=[rbac.models.validate_object_type]),
        ),
        migrations.AlterField(
            model_name='role',
            name='description',
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name='role',
            name='name',
            field=models.CharField(max_length=160),
        ),
        migrations.AddConstraint(
            model_name='role',
            constraint=models.UniqueConstraint(fields=('name', 'built_in'), name='unique_role'),
        ),
    ]

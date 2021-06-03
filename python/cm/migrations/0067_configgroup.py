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
# Generated by Django 3.2 on 2021-06-02 14:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('cm', '0066_auto_20210427_0853'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigGroup',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('object_id', models.PositiveIntegerField()),
                ('name', models.CharField(max_length=30)),
                ('description', models.TextField(blank=True)),
                ('config', models.JSONField(default=dict)),
                ('hosts', models.ManyToManyField(to='cm.Host', blank=True)),
                (
                    'object_type',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
    ]

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
# Generated by Django 2.2.5 on 2019-09-04 12:59
# pylint: disable=line-too-long


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cm', '0031_auto_20190926_1600'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubAction',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=160)),
                ('display_name', models.CharField(blank=True, max_length=160)),
                ('script', models.CharField(max_length=160)),
                (
                    'script_type',
                    models.CharField(
                        choices=[('ansible', 'ansible'), ('task_generator', 'task_generator')],
                        max_length=16,
                    ),
                ),
                ('state_on_fail', models.CharField(blank=True, max_length=64)),
                ('params', models.TextField(blank=True)),
                (
                    'action',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cm.Action'),
                ),
            ],
        ),
        migrations.CreateModel(
            name='StageSubAction',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=160)),
                ('display_name', models.CharField(blank=True, max_length=160)),
                ('script', models.CharField(max_length=160)),
                (
                    'script_type',
                    models.CharField(
                        choices=[('ansible', 'ansible'), ('task_generator', 'task_generator')],
                        max_length=16,
                    ),
                ),
                ('state_on_fail', models.CharField(blank=True, max_length=64)),
                ('params', models.TextField(blank=True)),
                (
                    'action',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='cm.StageAction'
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name='joblog', name='sub_action_id', field=models.PositiveIntegerField(default=0),
        ),
    ]

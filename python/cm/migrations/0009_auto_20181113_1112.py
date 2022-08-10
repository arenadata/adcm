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
# Generated by Django 2.0.5 on 2018-11-13 11:12
# pylint: disable=line-too-long

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cm', '0008_auto_20181107_1216'),
    ]

    operations = [
        migrations.CreateModel(
            name='HostProvider',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=80, unique=True)),
                ('description', models.TextField(blank=True)),
                ('state', models.CharField(default='created', max_length=64)),
                ('stack', models.TextField(blank=True)),
                (
                    'config',
                    models.OneToOneField(
                        null=True, on_delete=django.db.models.deletion.CASCADE, to='cm.ObjectConfig'
                    ),
                ),
            ],
        ),
        migrations.AlterField(
            model_name='prototype',
            name='type',
            field=models.CharField(
                choices=[
                    ('service', 'service'),
                    ('cluster', 'cluster'),
                    ('host', 'host'),
                    ('provider', 'provider'),
                ],
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='type',
            field=models.CharField(
                choices=[
                    ('service', 'service'),
                    ('cluster', 'cluster'),
                    ('host', 'host'),
                    ('provider', 'provider'),
                ],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='hostprovider',
            name='prototype',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cm.Prototype'),
        ),
        migrations.AddField(
            model_name='host',
            name='provider',
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='cm.HostProvider',
            ),
        ),
    ]

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

# Generated by Django 3.2.16 on 2023-01-19 07:55

from django.db import migrations, models

import cm.models


class Migration(migrations.Migration):

    dependencies = [
        ('cm', '0101_delete_dummydata'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='_venv',
            field=models.CharField(db_column='venv', default='default', max_length=1000),
        ),
        migrations.AlterField(
            model_name='action',
            name='display_name',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='action',
            name='script',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='action',
            name='script_type',
            field=models.CharField(
                choices=[('ansible', 'ansible'), ('task_generator', 'task_generator')], max_length=1000
            ),
        ),
        migrations.AlterField(
            model_name='action',
            name='state_on_fail',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='action',
            name='state_on_success',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='action',
            name='type',
            field=models.CharField(choices=[('task', 'task'), ('job', 'job')], max_length=1000),
        ),
        migrations.AlterField(
            model_name='adcm',
            name='name',
            field=models.CharField(choices=[('ADCM', 'ADCM')], max_length=1000, unique=True),
        ),
        migrations.AlterField(
            model_name='adcm',
            name='state',
            field=models.CharField(default='created', max_length=1000),
        ),
        migrations.AlterField(
            model_name='bundle',
            name='edition',
            field=models.CharField(default='community', max_length=1000),
        ),
        migrations.AlterField(
            model_name='bundle',
            name='hash',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='bundle',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='bundle',
            name='version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='cluster',
            name='name',
            field=models.CharField(max_length=1000, unique=True),
        ),
        migrations.AlterField(
            model_name='cluster',
            name='state',
            field=models.CharField(default='created', max_length=1000),
        ),
        migrations.AlterField(
            model_name='clusterobject',
            name='_maintenance_mode',
            field=models.CharField(
                choices=[('ON', 'ON'), ('OFF', 'OFF'), ('CHANGING', 'CHANGING')], default='OFF', max_length=1000
            ),
        ),
        migrations.AlterField(
            model_name='clusterobject',
            name='state',
            field=models.CharField(default='created', max_length=1000),
        ),
        migrations.AlterField(
            model_name='concernitem',
            name='cause',
            field=models.CharField(
                choices=[
                    ('config', 'config'),
                    ('job', 'job'),
                    ('host-component', 'host-component'),
                    ('import', 'import'),
                    ('service', 'service'),
                ],
                max_length=1000,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='concernitem',
            name='name',
            field=models.CharField(max_length=1000, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='concernitem',
            name='type',
            field=models.CharField(
                choices=[('lock', 'lock'), ('issue', 'issue'), ('flag', 'flag')], default='lock', max_length=1000
            ),
        ),
        migrations.AlterField(
            model_name='groupconfig',
            name='name',
            field=models.CharField(max_length=1000, validators=[cm.models.validate_line_break_character]),
        ),
        migrations.AlterField(
            model_name='host',
            name='fqdn',
            field=models.CharField(max_length=1000, unique=True),
        ),
        migrations.AlterField(
            model_name='host',
            name='maintenance_mode',
            field=models.CharField(
                choices=[('ON', 'ON'), ('OFF', 'OFF'), ('CHANGING', 'CHANGING')], default='OFF', max_length=1000
            ),
        ),
        migrations.AlterField(
            model_name='host',
            name='state',
            field=models.CharField(default='created', max_length=1000),
        ),
        migrations.AlterField(
            model_name='hostcomponent',
            name='state',
            field=models.CharField(default='created', max_length=1000),
        ),
        migrations.AlterField(
            model_name='hostprovider',
            name='name',
            field=models.CharField(max_length=1000, unique=True),
        ),
        migrations.AlterField(
            model_name='hostprovider',
            name='state',
            field=models.CharField(default='created', max_length=1000),
        ),
        migrations.AlterField(
            model_name='joblog',
            name='status',
            field=models.CharField(
                choices=[
                    ('created', 'created'),
                    ('success', 'success'),
                    ('failed', 'failed'),
                    ('running', 'running'),
                    ('locked', 'locked'),
                    ('aborted', 'aborted'),
                ],
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name='logstorage',
            name='format',
            field=models.CharField(choices=[('txt', 'txt'), ('json', 'json')], max_length=1000),
        ),
        migrations.AlterField(
            model_name='logstorage',
            name='type',
            field=models.CharField(
                choices=[('stdout', 'stdout'), ('stderr', 'stderr'), ('check', 'check'), ('custom', 'custom')],
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name='messagetemplate',
            name='name',
            field=models.CharField(max_length=1000, unique=True),
        ),
        migrations.AlterField(
            model_name='productcategory',
            name='value',
            field=models.CharField(max_length=1000, unique=True),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='adcm_min_version',
            field=models.CharField(default=None, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='display_name',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='license',
            field=models.CharField(
                choices=[('absent', 'absent'), ('accepted', 'accepted'), ('unaccepted', 'unaccepted')],
                default='absent',
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='license_hash',
            field=models.CharField(default=None, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='license_path',
            field=models.CharField(default=None, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='monitoring',
            field=models.CharField(
                choices=[('active', 'active'), ('passive', 'passive')], default='active', max_length=1000
            ),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='path',
            field=models.CharField(default='', max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='type',
            field=models.CharField(
                choices=[
                    ('adcm', 'adcm'),
                    ('cluster', 'cluster'),
                    ('service', 'service'),
                    ('component', 'component'),
                    ('provider', 'provider'),
                    ('host', 'host'),
                ],
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='venv',
            field=models.CharField(default='default', max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototype',
            name='version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototypeconfig',
            name='display_name',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototypeconfig',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototypeconfig',
            name='subname',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototypeconfig',
            name='type',
            field=models.CharField(
                choices=[
                    ('string', 'string'),
                    ('text', 'text'),
                    ('password', 'password'),
                    ('secrettext', 'secrettext'),
                    ('json', 'json'),
                    ('integer', 'integer'),
                    ('float', 'float'),
                    ('option', 'option'),
                    ('variant', 'variant'),
                    ('boolean', 'boolean'),
                    ('file', 'file'),
                    ('secretfile', 'secretfile'),
                    ('list', 'list'),
                    ('map', 'map'),
                    ('secretmap', 'secretmap'),
                    ('structure', 'structure'),
                    ('group', 'group'),
                ],
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name='prototypeexport',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototypeimport',
            name='max_version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototypeimport',
            name='min_version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='prototypeimport',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='servicecomponent',
            name='_maintenance_mode',
            field=models.CharField(
                choices=[('ON', 'ON'), ('OFF', 'OFF'), ('CHANGING', 'CHANGING')], default='OFF', max_length=1000
            ),
        ),
        migrations.AlterField(
            model_name='servicecomponent',
            name='state',
            field=models.CharField(default='created', max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageaction',
            name='_venv',
            field=models.CharField(db_column='venv', default='default', max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageaction',
            name='display_name',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageaction',
            name='script',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageaction',
            name='script_type',
            field=models.CharField(
                choices=[('ansible', 'ansible'), ('task_generator', 'task_generator')], max_length=1000
            ),
        ),
        migrations.AlterField(
            model_name='stageaction',
            name='state_on_fail',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageaction',
            name='state_on_success',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageaction',
            name='type',
            field=models.CharField(choices=[('task', 'task'), ('job', 'job')], max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='adcm_min_version',
            field=models.CharField(default=None, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='edition',
            field=models.CharField(default='community', max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='license',
            field=models.CharField(
                choices=[('absent', 'absent'), ('accepted', 'accepted'), ('unaccepted', 'unaccepted')],
                default='absent',
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='license_hash',
            field=models.CharField(default=None, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='license_path',
            field=models.CharField(default=None, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='monitoring',
            field=models.CharField(
                choices=[('active', 'active'), ('passive', 'passive')], default='active', max_length=1000
            ),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='path',
            field=models.CharField(default='', max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='type',
            field=models.CharField(
                choices=[
                    ('adcm', 'adcm'),
                    ('cluster', 'cluster'),
                    ('service', 'service'),
                    ('component', 'component'),
                    ('provider', 'provider'),
                    ('host', 'host'),
                ],
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='venv',
            field=models.CharField(default='default', max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototype',
            name='version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototypeconfig',
            name='display_name',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototypeconfig',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototypeconfig',
            name='subname',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototypeconfig',
            name='type',
            field=models.CharField(
                choices=[
                    ('string', 'string'),
                    ('text', 'text'),
                    ('password', 'password'),
                    ('secrettext', 'secrettext'),
                    ('json', 'json'),
                    ('integer', 'integer'),
                    ('float', 'float'),
                    ('option', 'option'),
                    ('variant', 'variant'),
                    ('boolean', 'boolean'),
                    ('file', 'file'),
                    ('secretfile', 'secretfile'),
                    ('list', 'list'),
                    ('map', 'map'),
                    ('secretmap', 'secretmap'),
                    ('structure', 'structure'),
                    ('group', 'group'),
                ],
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name='stageprototypeexport',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototypeimport',
            name='max_version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototypeimport',
            name='min_version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageprototypeimport',
            name='name',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stagesubaction',
            name='display_name',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='stagesubaction',
            name='script',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stagesubaction',
            name='script_type',
            field=models.CharField(
                choices=[('ansible', 'ansible'), ('task_generator', 'task_generator')], max_length=1000
            ),
        ),
        migrations.AlterField(
            model_name='stagesubaction',
            name='state_on_fail',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageupgrade',
            name='max_version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageupgrade',
            name='min_version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageupgrade',
            name='name',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='stageupgrade',
            name='state_on_success',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='subaction',
            name='display_name',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='subaction',
            name='script',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='subaction',
            name='script_type',
            field=models.CharField(
                choices=[('ansible', 'ansible'), ('task_generator', 'task_generator')], max_length=1000
            ),
        ),
        migrations.AlterField(
            model_name='subaction',
            name='state_on_fail',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='tasklog',
            name='status',
            field=models.CharField(
                choices=[
                    ('created', 'created'),
                    ('success', 'success'),
                    ('failed', 'failed'),
                    ('running', 'running'),
                    ('locked', 'locked'),
                    ('aborted', 'aborted'),
                ],
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name='upgrade',
            name='max_version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='upgrade',
            name='min_version',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='upgrade',
            name='name',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='upgrade',
            name='state_on_success',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='login',
            field=models.CharField(max_length=1000, unique=True),
        ),
    ]

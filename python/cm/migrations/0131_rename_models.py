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

from functools import partial

from django.db import migrations, models


def update_tasklog(apps, schema_editor, old_value: str, new_value: str):
    TaskLog = apps.get_model("cm", "TaskLog")
    TaskLog.objects.filter(owner_type=old_value).update(owner_type=new_value)


fix_tasklog = partial(update_tasklog, old_value="hostprovider", new_value="provider")
revert_tasklog = partial(update_tasklog, old_value="provider", new_value="hostprovider")


class Migration(migrations.Migration):
    dependencies = [
        ("cm", "0130_prepare_to_rename_models"),
    ]

    operations = [
        # Updating old records in the django_content_type table to avoid conflicts in the following queries,
        # see the ADCM-6265 task.
        migrations.RunSQL(
            sql="""
            UPDATE django_content_type
            SET model = 'stale_' || model
            WHERE app_label = 'cm'
              AND model in ('component', 'stagecomponent', 'dummydata', 'role', 'messagetemplate');
        """,
            reverse_sql="""
            UPDATE django_content_type
            SET model = replace(model, 'stale_', '')
            WHERE app_label = 'cm'
              AND model in ('stale_component', 'stale_stagecomponent', 'stale_dummydata', 'stale_role',
                            'stale_messagetemplate');
        """,
        ),
        migrations.RunSQL(
            sql="""
            UPDATE auth_permission
            SET codename = codename || '_stale'
            WHERE content_type_id in (SELECT id
                                      FROM django_content_type
                                      WHERE app_label = 'cm'
                                        AND model IN ('stale_component', 'stale_stagecomponent', 'stale_dummydata',
                                                      'stale_role', 'stale_messagetemplate'));
        """,
            reverse_sql="""
            UPDATE auth_permission
            SET codename = replace(codename, '_stale', '')
            WHERE content_type_id in (SELECT id
                                      FROM django_content_type
                                      WHERE app_label = 'cm'
                                        AND model IN ('stale_component', 'stale_stagecomponent', 'stale_dummydata',
                                                      'stale_role', 'stale_messagetemplate'));
            """,
        ),
        migrations.RenameModel(old_name="ClusterObject", new_name="Service"),
        migrations.RenameModel(old_name="ServiceComponent", new_name="Component"),
        migrations.RenameModel(old_name="HostProvider", new_name="Provider"),
        migrations.RenameModel(old_name="GroupConfig", new_name="ConfigHostGroup"),
        migrations.AlterField(
            model_name="tasklog",
            name="owner_type",
            field=models.CharField(
                choices=[
                    ("adcm", "adcm"),
                    ("cluster", "cluster"),
                    ("service", "service"),
                    ("component", "component"),
                    ("provider", "provider"),
                    ("host", "host"),
                ],
                max_length=100,
                null=True,
            ),
        ),
        migrations.RunPython(code=fix_tasklog, reverse_code=revert_tasklog),
    ]

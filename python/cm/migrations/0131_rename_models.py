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


def update_content_type(apps, schema_editor, old_model: str, new_model: str):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="cm", model=old_model).update(model=new_model)


fix_service_ct = partial(update_content_type, old_model="clusterobject", new_model="service")
revert_service_ct = partial(update_content_type, old_model="service", new_model="clusterobject")

fix_component_ct = partial(update_content_type, old_model="servicecomponent", new_model="component")
revert_component_ct = partial(update_content_type, old_model="component", new_model="servicecomponent")

fix_provider_ct = partial(update_content_type, old_model="hostprovider", new_model="provider")
revert_provider_ct = partial(update_content_type, old_model="provider", new_model="hostprovider")

fix_chg_ct = partial(update_content_type, old_model="groupconfig", new_model="confighostgroup")
revert_chg_ct = partial(update_content_type, old_model="confighostgroup", new_model="groupconfig")


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
        migrations.RenameModel(old_name="ClusterObject", new_name="Service"),
        migrations.RunPython(code=fix_service_ct, reverse_code=revert_service_ct),
        migrations.RenameModel(old_name="ServiceComponent", new_name="Component"),
        migrations.RunPython(code=fix_component_ct, reverse_code=revert_component_ct),
        migrations.RenameModel(old_name="HostProvider", new_name="Provider"),
        migrations.RunPython(code=fix_provider_ct, reverse_code=revert_provider_ct),
        migrations.RenameModel(old_name="GroupConfig", new_name="ConfigHostGroup"),
        migrations.RunPython(code=fix_chg_ct, reverse_code=revert_chg_ct),
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

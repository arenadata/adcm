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

# Generated by Django 3.2.17 on 2023-02-20 08:00

from django.db import migrations


def migrate_nginx_logrotate_config(apps, schema_editor) -> None:
    adcm_model = apps.get_model("cm", "ADCM")
    config_log_model = apps.get_model("cm", "ConfigLog")
    prototype_config_model = apps.get_model("cm", "PrototypeConfig")  # noqa: F841
    logrotate_conf_field_name = "logrotate"

    try:
        adcm_object = adcm_model.objects.get(pk=1)
    except adcm_model.DoesNotExist:
        return

    config_log = config_log_model.objects.get(obj_ref=adcm_object.config, pk=adcm_object.config.current)
    config_log.pk = None
    logrotate_attr = config_log.attr.get(logrotate_conf_field_name)
    if not logrotate_attr:
        return

    logrotate_is_active = logrotate_attr.get("active")
    if logrotate_is_active is None:
        return

    if not logrotate_is_active:
        return

    logrotate_attr["active"] = False

    config_log.save()
    config_log.obj_ref.previous = config_log.obj_ref.current
    config_log.obj_ref.current = config_log.pk
    config_log.obj_ref.save()


def reverse_migrate_nginx_logrotate_config(apps, schema_editor) -> None:
    ...


class Migration(migrations.Migration):
    dependencies = [
        ("cm", "0105_auto_20230220_0800"),
    ]

    operations = [
        migrations.RunPython(code=migrate_nginx_logrotate_config, reverse_code=reverse_migrate_nginx_logrotate_config),
    ]

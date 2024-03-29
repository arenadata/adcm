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

# Generated by Django 3.2.17 on 2023-06-21 12:26

from django.db import migrations, models

data = {
    "name": "outdated configuration flag",
    "template": {
        "message": "${source} has an outdated configuration",
        "placeholder": {
            "source": {"type": "adcm_entity"},
        },
    },
}


def insert_message_templates(apps, schema_editor):
    message_template = apps.get_model("cm", "MessageTemplate")
    message_template.objects.create(**data)


def insert_message_templates_revert(apps, schema_editor):
    message_template = apps.get_model("cm", "MessageTemplate")
    message_template.objects.filter(name=data["name"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cm", "0110_message_template_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="prototype",
            name="allow_flags",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="stageprototype",
            name="allow_flags",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(code=insert_message_templates, reverse_code=insert_message_templates_revert),
    ]

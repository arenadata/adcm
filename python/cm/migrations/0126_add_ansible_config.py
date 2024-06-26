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

# Generated by Django 3.2.23 on 2024-06-03 08:32

from django.db import migrations, models
import django.db.models.deletion


def add_defaults_for_existing_clusters(apps, schema_editor):
    AnsibleConfig = apps.get_model("cm", "AnsibleConfig")
    Cluster = apps.get_model("cm", "Cluster")
    ContentType = apps.get_model("contenttypes", "ContentType")

    default = {"defaults": {"forks": "5"}}

    content_type = ContentType.objects.get_for_model(Cluster)

    AnsibleConfig.objects.bulk_create(
        objs=[
            AnsibleConfig(value=default, object_id=cluster_id, object_type=content_type)
            for cluster_id in Cluster.objects.values_list("id", flat=True)
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("cm", "0125_simplify_defaults"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnsibleConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.JSONField(default=dict)),
                ("object_id", models.PositiveIntegerField()),
                (
                    "object_type",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="contenttypes.contenttype"),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="ansibleconfig",
            constraint=models.UniqueConstraint(fields=("object_id", "object_type"), name="unique_ansibleconfig"),
        ),
        migrations.RunPython(add_defaults_for_existing_clusters, migrations.RunPython.noop),
    ]

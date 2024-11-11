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


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cm", "0131_rename_models"),
    ]

    # In case of PostgreSQL db these operations do nothing
    # or just adds `related_name` (which still do nothing on sql level)
    # see cm 0130 migration, get_operations.__doc__
    operations = [
        # Service
        migrations.AlterField(
            model_name="clusterbind",
            name="service",
            field=models.ForeignKey(
                default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to="cm.service"
            ),
        ),
        migrations.AlterField(
            model_name="clusterbind",
            name="source_service",
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="source_service",
                to="cm.service",
            ),
        ),
        migrations.AlterField(
            model_name="hostcomponent",
            name="service",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cm.service"),
        ),
        migrations.AlterField(
            model_name="component",
            name="service",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cm.service"),
        ),
        migrations.AlterField(
            model_name="service",
            name="cluster",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="services", to="cm.cluster"
            ),
        ),
        # Component
        migrations.AlterField(
            model_name="hostcomponent",
            name="component",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cm.component"),
        ),
        migrations.AlterField(
            model_name="component",
            name="cluster",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="components", to="cm.cluster"
            ),
        ),
        migrations.AlterField(
            model_name="component",
            name="service",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="components", to="cm.service"
            ),
        ),
        # Provider
        migrations.AlterField(
            model_name="host",
            name="provider",
            field=models.ForeignKey(
                default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to="cm.provider"
            ),
        ),
        # ConfigHostGroup
        migrations.AlterField(
            model_name="confighostgroup",
            name="config",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="config_host_group",
                to="cm.objectconfig",
            ),
        ),
        migrations.AlterField(
            model_name="confighostgroup",
            name="hosts",
            field=models.ManyToManyField(blank=True, related_name="config_host_group", to="cm.Host"),
        ),
        migrations.AlterField(
            model_name="confighostgroup",
            name="object_type",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="contenttypes.contenttype"),
        ),
    ]

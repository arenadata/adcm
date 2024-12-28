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

# Generated by Django 3.2.23 on 2024-10-21 11:55


from django.db import connection, migrations, models


def get_operations() -> list[migrations.AlterField]:
    """
    PostgreSQL can handle models renaming without preparation
    SQLite can't, so we have to:
        1. unlink related models from models we want to rename preserving data (change FKs to IntegerFields)
        2. rename models
        3. restore FKs from p. 1
    """

    match connection.vendor:
        case "postgresql":
            return []
        case "sqlite":
            return [
                # Prepare to rename ClusterObject to Service
                migrations.AlterField(
                    model_name="clusterbind",
                    name="service",
                    field=models.IntegerField(default=None, null=True),
                ),
                migrations.AlterField(
                    model_name="clusterbind",
                    name="source_service",
                    field=models.IntegerField(default=None, null=True),
                ),
                migrations.AlterField(
                    model_name="hostcomponent",
                    name="service",
                    field=models.IntegerField(),
                ),
                migrations.AlterField(
                    model_name="servicecomponent",
                    name="service",
                    field=models.IntegerField(),
                ),
                # Prepare to rename ServiceComponent to Component
                migrations.AlterField(
                    model_name="hostcomponent",
                    name="component",
                    field=models.IntegerField(),
                ),
                # Prepare to rename HostProvider to Provider
                migrations.AlterField(
                    model_name="host",
                    name="provider",
                    field=models.IntegerField(default=None, null=True),
                ),
                # Prepare to rename GroupConfig to ConfigHostGroup
                migrations.AlterField(
                    model_name="groupconfig",
                    name="config",
                    field=models.IntegerField(default=None, null=True),
                ),
                migrations.AlterField(
                    model_name="groupconfig",
                    name="object_type",
                    field=models.IntegerField(),
                ),
            ]
        case _:
            # it is not clear how other databases behave in such case,
            # needs to be investigated when(if) new db backend support is added
            raise NotImplementedError


class Migration(migrations.Migration):
    dependencies = [
        ("cm", "0129_auto_20240904_1045"),
    ]

    operations = [
        # remove ClusterObject's self FK
        migrations.RemoveField(
            model_name="clusterobject",
            name="service",
        ),
        *get_operations(),
    ]
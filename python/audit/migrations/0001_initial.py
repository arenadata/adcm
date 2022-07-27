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
# Generated by Django 3.2.13 on 2022-07-19 11:00

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditObject',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('object_id', models.PositiveIntegerField()),
                ('object_name', models.CharField(max_length=160)),
                (
                    'object_type',
                    models.CharField(
                        choices=[
                            ('cluster', 'cluster'),
                            ('service', 'service'),
                            ('component', 'component'),
                            ('host', 'host'),
                            ('provider', 'provider'),
                            ('bundle', 'bundle'),
                            ('adcm', 'adcm'),
                            ('user', 'user'),
                            ('group', 'group'),
                            ('role', 'role'),
                            ('policy', 'policy'),
                        ],
                        max_length=16,
                    ),
                ),
                ('is_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='AuditSession',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'login_result',
                    models.CharField(
                        choices=[
                            ('success', 'success'),
                            ('wrong_password', 'wrong_password'),
                            ('account_disabled', 'account_disabled'),
                            ('user_not_found', 'user_not_found'),
                        ],
                        max_length=64,
                    ),
                ),
                ('login_time', models.DateTimeField(auto_now_add=True)),
                (
                    'user',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('operation_name', models.CharField(max_length=160)),
                (
                    'operation_type',
                    models.CharField(
                        choices=[('create', 'create'), ('update', 'update'), ('delete', 'delete')],
                        max_length=16,
                    ),
                ),
                (
                    'operation_result',
                    models.CharField(
                        choices=[
                            ('success', 'success'),
                            ('failed', 'failed'),
                            ('in_progress', 'in_progress'),
                        ],
                        max_length=16,
                    ),
                ),
                ('operation_time', models.DateTimeField(auto_now_add=True)),
                ('object_changes', models.JSONField(default=dict)),
                (
                    'audit_object',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='audit.auditobject',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
        ),
    ]
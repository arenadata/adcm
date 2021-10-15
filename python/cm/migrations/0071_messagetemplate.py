# Generated by Django 3.2 on 2021-07-22 07:18

from django.db import migrations, models

data = [
    {
        'name': 'locked by action on target',
        'template': {
            'message': 'Object was locked by running action ${action} on ${target}',
            'placeholder': {
                'action': {'type': 'action'},
                'target': {'type': 'adcm_entity'},
            },
        },
    },
]


def insert_message_templates(apps, schema_editor):
    MessageTemplate = apps.get_model('cm', 'MessageTemplate')
    MessageTemplate.objects.bulk_create([MessageTemplate(**kwargs) for kwargs in data])


class Migration(migrations.Migration):

    dependencies = [
        ('cm', '0070_lock_refactoring'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageTemplate',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('name', models.CharField(max_length=160, unique=True)),
                ('template', models.JSONField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunPython(insert_message_templates),
    ]

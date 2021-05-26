# Generated by Django 3.1.2 on 2021-05-21 14:49
# pylint: disable=line-too-long

from django.db import migrations, models
import django.db.models.deletion


def copy_model(All, Model):
    for obj in Model.objects.all():
        obj_type = obj.prototype.type
        new = All(
            type=obj_type,
            legacy_id=obj.id,
            prototype=obj.prototype,
            config=obj.config,
            state=obj.state,
            stack=obj.stack,
            issue=obj.issue,
        )
        if hasattr(obj, 'name'):
            new.name = obj.name
        if hasattr(obj, 'description'):
            new.description = obj.description
        if hasattr(obj, 'fqdn'):
            new.name = obj.fqdn
        new.save()
        obj.super = new
        obj.save()
        if obj_type == 'service':
            new.parent = obj.cluster.super
        elif obj_type == 'component':
            new.parent = obj.service.super
        elif obj_type == 'host':
            new.parent = obj.provider.super
            if obj.cluster:
                new.belong = obj.cluster.super
        new.save()


def populate_all_objects(apps, schema_editor):
    All = apps.get_model('cm', 'AllObjects')
    copy_model(All, apps.get_model('cm', 'ADCM'))
    copy_model(All, apps.get_model('cm', 'Cluster'))
    copy_model(All, apps.get_model('cm', 'HostProvider'))
    copy_model(All, apps.get_model('cm', 'Host'))
    copy_model(All, apps.get_model('cm', 'ClusterObject'))
    copy_model(All, apps.get_model('cm', 'ServiceComponent'))


class Migration(migrations.Migration):

    dependencies = [
        ('cm', '0066_auto_20210427_0853'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicecomponent',
            name='prototype',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cm.prototype'),
        ),
        migrations.CreateModel(
            name='AllObjects',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('adcm', 'adcm'), ('service', 'service'), ('component', 'component'), ('cluster', 'cluster'), ('host', 'host'), ('provider', 'provider')], max_length=16)),
                ('legacy_id', models.PositiveIntegerField(null=True)),
                ('name', models.CharField(max_length=80, null=True)),
                ('description', models.TextField(blank=True)),
                ('state', models.CharField(default='created', max_length=64)),
                ('stack', models.JSONField(default=list)),
                ('issue', models.JSONField(default=dict)),
                ('belong', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='belonged', to='cm.allobjects')),
                ('config', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='cm.objectconfig')),
                ('parent', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='childs', to='cm.allobjects')),
                ('prototype', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cm.prototype')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='adcm',
            name='super',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='cm.allobjects'),
        ),
        migrations.AddField(
            model_name='cluster',
            name='super',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='cm.allobjects'),
        ),
        migrations.AddField(
            model_name='clusterobject',
            name='super',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='cm.allobjects'),
        ),
        migrations.AddField(
            model_name='host',
            name='super',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='cm.allobjects'),
        ),
        migrations.AddField(
            model_name='hostprovider',
            name='super',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='cm.allobjects'),
        ),
        migrations.AddField(
            model_name='servicecomponent',
            name='super',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='cm.allobjects'),
        ),
        migrations.RunPython(populate_all_objects),
    ]

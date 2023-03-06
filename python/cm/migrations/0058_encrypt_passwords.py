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

import json

from cm.adcm_config import ansible_encrypt_and_format
from cm.utils import obj_to_dict
from django.db import migrations


def get_prototype_config(proto, PrototypeConfig):
    spec = {}
    flist = ("default", "required", "type", "limits")

    for c in PrototypeConfig.objects.filter(prototype=proto, action=None, type="group").order_by("id"):
        spec[c.name] = {}

    for c in PrototypeConfig.objects.filter(prototype=proto, action=None).order_by("id"):
        if c.subname == "":
            if c.type != "group":
                spec[c.name] = obj_to_dict(c, flist)
        else:
            spec[c.name][c.subname] = obj_to_dict(c, flist)
    return spec


def process_password(spec, conf):
    def update_password(passwd):
        if "$ANSIBLE_VAULT;" in passwd:
            return passwd
        return ansible_encrypt_and_format(passwd)

    for key in conf:
        if key not in spec:
            continue
        if "type" in spec[key]:
            if spec[key]["type"] == "password" and conf[key]:
                conf[key] = update_password(conf[key])
        else:
            if not conf[key]:
                continue
            for subkey in conf[key]:
                if subkey not in spec[key]:
                    continue
                if spec[key][subkey]["type"] == "password" and conf[key][subkey]:
                    conf[key][subkey] = update_password(conf[key][subkey])
    return conf


def process_objects(obj, ConfigLog, PrototypeConfig):
    spec = get_prototype_config(obj.prototype, PrototypeConfig)
    if not spec:
        return
    for cl in ConfigLog.objects.filter(obj_ref=obj.config):
        conf = json.loads(cl.config)
        process_password(spec, conf)
        cl.config = json.dumps(conf)
        cl.save()


def encrypt_passwords(apps, schema_editor):
    ConfigLog = apps.get_model("cm", "ConfigLog")
    PrototypeConfig = apps.get_model("cm", "PrototypeConfig")
    for model_name in "Cluster", "ClusterObject", "HostProvider", "Host", "ADCM":
        Model = apps.get_model("cm", model_name)
        for obj in Model.objects.filter(config__isnull=False):
            process_objects(obj, ConfigLog, PrototypeConfig)


class Migration(migrations.Migration):
    dependencies = [
        ("cm", "0057_auto_20200831_1055"),
    ]

    operations = [
        migrations.RunPython(encrypt_passwords),
    ]

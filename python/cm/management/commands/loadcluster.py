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

# pylint: disable=too-many-locals, global-statement

import base64
import getpass
import json
import sys
from datetime import datetime

from ansible.parsing.vault import VaultAES256, VaultSecret
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django.db.utils import IntegrityError

from cm.adcm_config import save_file_type
from cm.errors import AdcmEx
from cm.models import (
    Bundle,
    Cluster,
    ClusterObject,
    ConfigLog,
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    ObjectConfig,
    Prototype,
    PrototypeConfig,
    ServiceComponent,
)

OLD_ADCM_PASSWORD = None


def deserializer_datetime_fields(obj, fields=None):
    """
    Modifies fields of type ISO string to datetime type

    :param obj: Object in dictionary format
    :type obj: dict
    :param fields: List of fields in ISO string format
    :type fields: list
    """
    if obj is not None and fields is not None:
        for field in fields:
            obj[field] = datetime.fromisoformat(obj[field])


def get_prototype(**kwargs):
    """
    Returns prototype object

    :param kwargs: Parameters for finding a prototype
    :return: Prototype object
    :rtype: models.Prototype
    """
    bundle = Bundle.objects.get(hash=kwargs.pop("bundle_hash"))
    prototype = Prototype.objects.get(bundle=bundle, **kwargs)
    return prototype


def create_config(config, prototype=None):
    """
    Creating current ConfigLog, previous ConfigLog and ObjectConfig objects

    :param config: ConfigLog object in dictionary format
    :type config: dict
    :return: ObjectConfig object
    :rtype: models.ObjectConfig
    """
    if config is not None:
        current_config = process_config(prototype, config["current"])
        deserializer_datetime_fields(current_config, ["date"])
        previous_config = process_config(prototype, config["previous"])
        deserializer_datetime_fields(previous_config, ["date"])

        conf = ObjectConfig.objects.create(current=0, previous=0)

        current = ConfigLog.objects.create(obj_ref=conf, **current_config)
        current_id = current.id
        if previous_config is not None:
            previous = ConfigLog.objects.create(obj_ref=conf, **previous_config)
            previous_id = previous.id
        else:
            previous_id = 0

        conf.current = current_id
        conf.previous = previous_id
        conf.save()
        return conf
    else:
        return None


def create_group(group, ex_hosts_list, obj):
    """
    Creating GroupConfig object

    :param group: GroupConfig object in dictionary format
    :type group: dict
    :param ex_hosts_list: Map of ex_host_ids and new hosts
    :type ex_hosts_list: dict
    :return: GroupConfig object
    :rtype: models.GroupConfig
    """
    model_name = group.pop("model_name")
    ex_object_id = group.pop("object_id")
    group.pop("object_type")
    config = create_config(group.pop("config"))
    hosts = []
    for host in group.pop("hosts"):
        hosts.append(ex_hosts_list[host])
    gc = GroupConfig.objects.create(
        object_id=obj.id,
        config=config,
        object_type=ContentType.objects.get(model=model_name),
        **group,
    )
    gc.hosts.set(hosts)
    return ex_object_id, gc


def switch_encoding(msg):
    ciphertext = msg
    if settings.ANSIBLE_VAULT_HEADER in msg:
        _, ciphertext = msg.split("\n")
    vault = VaultAES256()
    secret_old = VaultSecret(bytes(OLD_ADCM_PASSWORD, settings.ENCODING_UTF_8))
    data = str(vault.decrypt(ciphertext, secret_old), settings.ENCODING_UTF_8)
    secret_new = VaultSecret(bytes(settings.ANSIBLE_SECRET, settings.ENCODING_UTF_8))
    ciphertext = vault.encrypt(bytes(data, settings.ENCODING_UTF_8), secret_new)
    return f"{settings.ANSIBLE_VAULT_HEADER}\n{str(ciphertext, settings.ENCODING_UTF_8)}"


def process_config(proto, config):
    if config is not None and proto is not None:
        conf = config["config"]
        for pconf in PrototypeConfig.objects.filter(
            prototype=proto, type__in=("secrettext", "password")
        ):
            if pconf.subname and conf[pconf.name][pconf.subname]:
                conf[pconf.name][pconf.subname] = switch_encoding(conf[pconf.name][pconf.subname])
            elif conf.get(pconf.name) and not pconf.subname:
                conf[pconf.name] = switch_encoding(conf[pconf.name])
        config["config"] = conf
    return config


def create_file_from_config(obj, config):
    if config is not None:
        conf = config["current"]["config"]
        proto = obj.prototype
        for pconf in PrototypeConfig.objects.filter(prototype=proto, type="file"):
            if pconf.subname and conf[pconf.name].get(pconf.subname):
                save_file_type(obj, pconf.name, pconf.subname, conf[pconf.name][pconf.subname])
            elif conf.get(pconf.name):
                save_file_type(obj, pconf.name, "", conf[pconf.name])


def create_cluster(cluster):
    """
    Creating Cluster object

    :param cluster: Cluster object in dictionary format
    :type cluster: dict
    :return: Cluster object
    :rtype: models.Cluster
    """
    try:
        Cluster.objects.get(name=cluster["name"])
        raise AdcmEx("CLUSTER_CONFLICT", "Cluster with the same name already exist")
    except Cluster.DoesNotExist:
        prototype = get_prototype(bundle_hash=cluster.pop("bundle_hash"), type="cluster")
        ex_id = cluster.pop("id")
        config = cluster.pop("config")
        cluster = Cluster.objects.create(
            prototype=prototype, config=create_config(config, prototype), **cluster
        )
        create_file_from_config(cluster, config)
        return ex_id, cluster


def create_provider(provider):
    """
    Creating HostProvider object

    :param provider: HostProvider object in dictionary format
    :type provider: dict
    :return: HostProvider object
    :rtype: models.HostProvider
    """
    bundle_hash = provider.pop("bundle_hash")
    ex_id = provider.pop("id")
    try:
        same_name_provider = HostProvider.objects.get(name=provider["name"])
        if same_name_provider.prototype.bundle.hash != bundle_hash:
            raise IntegrityError("Name of provider already in use in another bundle")
        create_file_from_config(same_name_provider, provider["config"])
        return ex_id, same_name_provider
    except HostProvider.DoesNotExist:
        prototype = get_prototype(bundle_hash=bundle_hash, type="provider")
        config = provider.pop("config")
        provider = HostProvider.objects.create(
            prototype=prototype, config=create_config(config, prototype), **provider
        )
        create_file_from_config(provider, config)
        return ex_id, provider


def create_host(host, cluster):
    """
    Creating Host object

    :param host: Host object in dictionary format
    :type host: dict
    :param cluster: Cluster object
    :type cluster: models.Cluster
    :return: Host object
    :rtype: models.Host
    """
    host.pop("provider")
    provider = HostProvider.objects.get(name=host.pop("provider__name"))
    try:
        Host.objects.get(fqdn=host["fqdn"])
        provider.delete()
        cluster.delete()
        raise AdcmEx("HOST_CONFLICT", "Host fqdn already in use")
    except Host.DoesNotExist:
        prototype = get_prototype(bundle_hash=host.pop("bundle_hash"), type="host")
        ex_id = host.pop("id")
        config = host.pop("config")
        new_host = Host.objects.create(
            prototype=prototype,
            provider=provider,
            config=create_config(config, prototype),
            cluster=cluster,
            **host,
        )
        create_file_from_config(new_host, config)
        return ex_id, new_host


def create_service(service, cluster):
    """
    Creating Service object

    :param service: ClusterObject object in dictionary format
    :type service: dict
    :param cluster: Cluster object
    :type cluster: models.Cluster
    :return: ClusterObject object
    :rtype: models.ClusterObject
    """
    prototype = get_prototype(
        bundle_hash=service.pop("bundle_hash"), type="service", name=service.pop("prototype__name")
    )
    ex_id = service.pop("id")
    config = service.pop("config")
    service = ClusterObject.objects.create(
        prototype=prototype, cluster=cluster, config=create_config(config, prototype), **service
    )
    create_file_from_config(service, config)
    return ex_id, service


def create_component(component, cluster, service):
    """
    Creating Component object

    :param component: ServiceComponent object in dictionary format
    :type component: dict
    :param cluster: Cluster object
    :type cluster: models.Cluster
    :param service: Service object
    :type service: models.ClusterObject
    :return: Component object
    :rtype: models.ServiceComponent
    """
    prototype = get_prototype(
        bundle_hash=component.pop("bundle_hash"),
        type="component",
        name=component.pop("prototype__name"),
        parent=service.prototype,
    )
    ex_id = component.pop("id")
    config = component.pop("config")
    component = ServiceComponent.objects.create(
        prototype=prototype,
        cluster=cluster,
        service=service,
        config=create_config(config, prototype),
        **component,
    )
    create_file_from_config(component, config)
    return ex_id, component


def create_host_component(host_component, cluster, host, service, component):
    """
    Creating HostComponent object

    :param host_component: HostComponent object in dictionary format
    :type host_component: dict
    :param cluster: Cluster object
    :type cluster: models.Cluster
    :param host: Host object
    :type host: models.Host
    :param service: Service object
    :type service: models.ClusterObject
    :param component: Component object
    :type component: models.ServiceComponent
    :return: HostComponent object
    :rtype: models.HostComponent
    """
    host_component.pop("cluster")
    host_component = HostComponent.objects.create(
        cluster=cluster, host=host, service=service, component=component, **host_component
    )
    return host_component


def check(data):
    """
    Checking cluster load

    :param data: Data from file
    :type data: dict
    """
    if settings.ADCM_VERSION != data["ADCM_VERSION"]:
        raise AdcmEx(
            "DUMP_LOAD_ADCM_VERSION_ERROR",
            msg=(
                f"ADCM versions do not match, dump version: {data['ADCM_VERSION']},"
                f" load version: {settings.ADCM_VERSION}"
            ),
        )

    for bundle_hash, bundle in data["bundles"].items():
        try:
            Bundle.objects.get(hash=bundle_hash)
        except Bundle.DoesNotExist as err:
            raise AdcmEx(
                "DUMP_LOAD_BUNDLE_ERROR",
                msg=f"Bundle '{bundle['name']} {bundle['version']}' not found",
            ) from err


def decrypt_file(pass_from_user, file):
    password = pass_from_user.encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=settings.DEFAULT_SALT,
        iterations=390000,
        backend=default_backend(),
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    f = Fernet(key)
    decrypted = f.decrypt(file.encode())
    return decrypted


def set_old_password(password):
    global OLD_ADCM_PASSWORD
    OLD_ADCM_PASSWORD = password


@atomic
def load(file_path):
    """
    Loading and creating objects from JSON file

    :param file_path: Path to JSON file
    :type file_path: str
    """
    try:
        password = getpass.getpass()
        with open(file_path, "r", encoding=settings.ENCODING_UTF_8) as f:
            encrypted = f.read()
            decrypted = decrypt_file(password, encrypted)
            data = json.loads(decrypted.decode(settings.ENCODING_UTF_8))
    except FileNotFoundError as err:
        raise AdcmEx("DUMP_LOAD_CLUSTER_ERROR", msg="Loaded file not found") from err
    except InvalidToken as err:
        raise AdcmEx("WRONG_PASSWORD") from err

    check(data)
    set_old_password(data["adcm_password"])
    _, cluster = create_cluster(data["cluster"])

    ex_provider_ids = {}
    for provider_data in data["providers"]:
        ex_provider_id, provider = create_provider(provider_data)
        ex_provider_ids[ex_provider_id] = provider

    ex_host_ids = {}
    for host_data in data["hosts"]:
        ex_host_id, host = create_host(host_data, cluster)
        ex_host_ids[ex_host_id] = host

    ex_service_ids = {}
    for service_data in data["services"]:
        ex_service_id, service = create_service(service_data, cluster)
        ex_service_ids[ex_service_id] = service

    ex_component_ids = {}
    for component_data in data["components"]:
        ex_component_id, component = create_component(
            component_data, cluster, ex_service_ids[component_data.pop("service")]
        )
        ex_component_ids[ex_component_id] = component

    for host_component_data in data["host_components"]:
        create_host_component(
            host_component_data,
            cluster,
            ex_host_ids[host_component_data.pop("host")],
            ex_service_ids[host_component_data.pop("service")],
            ex_component_ids[host_component_data.pop("component")],
        )
    for group_data in data["groups"]:
        if group_data["model_name"] == "cluster":
            obj = cluster
        elif group_data["model_name"] == "clusterobject":
            obj = ex_service_ids[group_data["object_id"]]
        elif group_data["model_name"] == "servicecomponent":
            obj = ex_component_ids[group_data["object_id"]]
        elif group_data["model_name"] == "hostprovider":
            obj = ex_provider_ids[group_data["object_id"]]
        create_group(group_data, ex_host_ids, obj)
    sys.stdout.write(f"Load successfully ended, cluster {cluster.display_name} created\n")


class Command(BaseCommand):
    """
    Command for load cluster object from JSON file

    Example:
        manage.py loadcluster cluster.json
    """

    help = "Load cluster object from JSON format"

    def add_arguments(self, parser):
        """Parsing command line arguments"""
        parser.add_argument("file_path", nargs="?")

    def handle(self, *args, **options):
        """Handler method"""
        file_path = options.get("file_path")
        load(file_path)

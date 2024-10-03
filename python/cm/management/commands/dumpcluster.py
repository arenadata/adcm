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

from pathlib import Path
import sys
import json
import base64
import getpass

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.core.management.base import BaseCommand

from cm.models import (
    Bundle,
    Cluster,
    Component,
    ConfigHostGroup,
    ConfigLog,
    Host,
    HostComponent,
    HostProvider,
    ObjectConfig,
    Prototype,
    Service,
)


def serialize_datetime_fields(obj, fields=None):
    """
    Modifies fields of type datetime to ISO string

    :param obj: Object in dictionary format
    :type obj: dict
    :param fields: List of fields in datetime format
    :type fields: list
    """
    if fields is not None:
        for field in fields:
            obj[field] = obj[field].isoformat()


def get_object(model, object_id, fields, datetime_fields=None):
    """
    The object is returned in dictionary format

    :param model: Type object
    :param object_id: Object ID
    :type object_id: int
    :param fields: List of fields
    :type fields: tuple
    :param datetime_fields: List of fields in datetime format
    :type datetime_fields: list
    :return: Object in dictionary format
    :rtype: dict
    """
    obj = model.objects.values(*fields).get(id=object_id)
    serialize_datetime_fields(obj, datetime_fields)
    return obj


def get_objects(model, fields, filters, datetime_fields=None):
    objects = list(model.objects.filters(**filters).values(*fields))
    for obj in objects:
        serialize_datetime_fields(obj, datetime_fields)
    return objects


def get_bundle(prototype_id):
    """
    Returns bundle object in dictionary format

    :param prototype_id: Prototype object ID
    :type prototype_id: int
    :return: Bundle object
    :rtype: dict
    """
    fields = ("name", "version", "edition", "hash", "description")
    prototype = Prototype.objects.get(id=prototype_id)
    return get_object(Bundle, prototype.bundle_id, fields)


def get_bundle_hash(prototype_id):
    """
    Returns the hash of the bundle

    :param prototype_id: Object ID
    :type prototype_id: int
    :return: The hash of the bundle
    :rtype: str
    """
    bundle = get_bundle(prototype_id)
    return bundle["hash"]


def get_config(object_config_id):
    """
    Returns current and previous config

    :param object_config_id:
    :type object_config_id: int
    :return: Current and previous config in dictionary format
    :rtype: dict
    """
    fields = ("config", "attr", "date", "description")
    try:
        object_config = ObjectConfig.objects.get(id=object_config_id)
    except ObjectConfig.DoesNotExist:
        return None
    config = {}
    for name in ["current", "previous"]:
        _id = getattr(object_config, name)
        if _id:
            config[name] = get_object(ConfigLog, _id, fields, ["date"])
        else:
            config[name] = None
    return config


def get_groups(object_id, model_name):
    """Return list of groups. Each group contain dictionary with all needed information

    :param object_id: Object ID
    :type object_id: int
    :param model_name: name of Type Object
    :type model_name: str
    :return: List with GroupConfig on that object in dict format
    :rtype: list
    """

    fields = ("object_id", "name", "description", "config", "object_type")
    groups = []
    for host_group in ConfigHostGroup.objects.filter(object_id=object_id, object_type__model=model_name):
        group = get_object(ConfigHostGroup, host_group.id, fields)
        group["config"] = get_config(group["config"])
        group["model_name"] = model_name
        group["hosts"] = [host.id for host in host_group.hosts.order_by("id")]
        groups.append(group)

    return groups


def get_cluster(cluster_id):
    """
    Returns cluster object in dictionary format

    :param cluster_id: Object ID
    :type cluster_id: int
    :return: Cluster object
    :rtype: dict
    """
    fields = (
        "id",
        "name",
        "description",
        "config",
        "state",
        "prototype",
        "_multi_state",
    )
    cluster = get_object(Cluster, cluster_id, fields)
    cluster["config"] = get_config(cluster["config"])
    bundle = get_bundle(cluster.pop("prototype"))
    cluster["bundle_hash"] = bundle["hash"]
    return cluster, bundle


def get_provider(provider_id):
    """
    Returns provider object in dictionary format

    :param provider_id: Object ID
    :type provider_id: int
    :return: Provider object
    :rtype: dict
    """
    fields = (
        "id",
        "prototype",
        "name",
        "description",
        "config",
        "state",
        "_multi_state",
    )
    provider = get_object(HostProvider, provider_id, fields)
    provider["config"] = get_config(provider["config"])
    bundle = get_bundle(provider.pop("prototype"))
    provider["bundle_hash"] = bundle["hash"]
    return provider, bundle


def get_host(host_id):
    """
    Returns host object in dictionary format

    :param host_id: Object ID
    :type host_id: int
    :return: Host object
    :rtype: dict
    """
    fields = (
        "id",
        "prototype",
        "fqdn",
        "description",
        "provider",
        "provider__name",
        "config",
        "state",
        "_multi_state",
    )
    host = get_object(Host, host_id, fields)
    host["config"] = get_config(host["config"])
    host["bundle_hash"] = get_bundle_hash(host.pop("prototype"))
    return host


def get_service(service_id):
    """
    Returns service object in dictionary format

    :param service_id: Object ID
    :type service_id: int
    :return: Service object
    :rtype: dict
    """
    fields = (
        "id",
        "prototype",
        "prototype__name",
        "config",
        "state",
        "_multi_state",
    )
    service = get_object(Service, service_id, fields)
    service["config"] = get_config(service["config"])
    service["bundle_hash"] = get_bundle_hash(service.pop("prototype"))
    return service


def get_component(component_id):
    """
    Returns component object in dictionary format

    :param component_id: Object ID
    :type component_id: int
    :return: Component object
    :rtype: dict
    """
    fields = (
        "id",
        "prototype",
        "prototype__name",
        "service",
        "config",
        "state",
        "_multi_state",
    )
    component = get_object(Component, component_id, fields)
    component["config"] = get_config(component["config"])
    component["bundle_hash"] = get_bundle_hash(component.pop("prototype"))
    return component


def get_host_component(host_component_id):
    """
    Returns host_component object in dictionary format

    :param host_component_id: Object ID
    :type host_component_id: int
    :return: HostComponent object
    :rtype: dict
    """
    fields = (
        "cluster",
        "host",
        "service",
        "component",
        "state",
    )
    return get_object(HostComponent, host_component_id, fields)


def encrypt_data(pass_from_user, result):
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
    return f.encrypt(result)


def dump(cluster_id, output):
    """
    Saving objects to file in JSON format

    :param cluster_id: Object ID
    :type cluster_id: int
    :param output: Path to file
    :type output: str
    """
    cluster, bundle = get_cluster(cluster_id)

    data = {
        "ADCM_VERSION": settings.ADCM_VERSION,
        "bundles": {
            bundle["hash"]: bundle,
        },
        "cluster": cluster,
        "hosts": [],
        "providers": [],
        "services": [],
        "components": [],
        "host_components": [],
        "groups": [],
    }

    provider_ids = set()
    data["groups"].extend(get_groups(cluster_id, "cluster"))

    for host_obj in Host.objects.filter(cluster_id=cluster["id"]):
        host = get_host(host_obj.id)
        provider_ids.add(host["provider"])
        data["hosts"].append(host)

    host_ids = [host["id"] for host in data["hosts"]]

    for provider_obj in HostProvider.objects.filter(id__in=provider_ids):
        provider, bundle = get_provider(provider_obj.id)
        data["providers"].append(provider)
        data["groups"].extend(get_groups(provider_obj.id, "hostprovider"))
        data["bundles"][bundle["hash"]] = bundle

    for service_obj in Service.objects.filter(cluster_id=cluster["id"]):
        service = get_service(service_obj.id)
        data["groups"].extend(get_groups(service_obj.id, "service"))
        data["services"].append(service)

    service_ids = [service["id"] for service in data["services"]]

    for component_obj in Component.objects.filter(cluster_id=cluster["id"], service_id__in=service_ids):
        component = get_component(component_obj.id)
        data["groups"].extend(get_groups(component_obj.id, "component"))
        data["components"].append(component)

    component_ids = [component["id"] for component in data["components"]]

    for host_component_obj in HostComponent.objects.filter(
        cluster_id=cluster["id"],
        host_id__in=host_ids,
        service_id__in=service_ids,
        component_id__in=component_ids,
    ):
        host_component = get_host_component(host_component_obj.id)
        data["host_components"].append(host_component)
    data["adcm_password"] = settings.ANSIBLE_SECRET
    result = json.dumps(data, indent=2).encode(settings.ENCODING_UTF_8)
    password = getpass.getpass()
    encrypted = encrypt_data(password, result)

    if output is not None:
        with Path(output).open(mode="wb") as f:
            f.write(encrypted)
        sys.stdout.write(f"Dump successfully done to file {output}\n")
    else:
        sys.stdout.write(encrypted.decode(settings.ENCODING_UTF_8))


class Command(BaseCommand):
    """
    Command for dump cluster object to JSON format

    Example:
        manage.py dumpcluster --cluster_id 1 --output cluster.json
    """

    help = "Dump cluster object to JSON format"

    def add_arguments(self, parser):
        """
        Parsing command line arguments
        """
        parser.add_argument(
            "-c",
            "--cluster_id",
            action="store",
            dest="cluster_id",
            required=True,
            type=int,
            help="Cluster ID",
        )
        parser.add_argument("-o", "--output", help="Specifies file to which the output is written.")

    def handle(self, *args, **options):  # noqa: ARG002
        """Handler method"""
        cluster_id = options["cluster_id"]
        output = options["output"]
        dump(cluster_id, output)

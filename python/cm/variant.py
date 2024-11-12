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

from functools import wraps
from typing import Callable

from django.core.exceptions import ObjectDoesNotExist

from cm.errors import AdcmEx
from cm.errors import raise_adcm_ex as err
from cm.logger import logger
from cm.models import (
    Cluster,
    Component,
    ConfigHostGroup,
    Host,
    HostComponent,
    Prototype,
    Service,
)


def return_empty_on_not_found(func: Callable) -> Callable:
    """
    There are some cases when variant predicate target object doesn't exist
    (e.g. service not added, but hosts on it are required in cluster's config).
    Use this function to return empty list instead of throwing error,
    otherwise each call to get_variant that'll call error-throwing function
    will result in something like 404/500 (based on type of raised Exception).

    Originally introduced as part of solution for ADCM-4778
    """

    @wraps(func)
    def with_not_found_handle(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ObjectDoesNotExist:
            return []

    return with_not_found_handle


def get_cluster(obj) -> Cluster | None:
    if isinstance(obj, ConfigHostGroup):
        obj = obj.object

    match obj.prototype.type:
        case "cluster":
            return obj
        case "service" | "component":
            return obj.cluster
        case "host":
            return obj.cluster
        case _:
            return None


def variant_service_in_cluster(**kwargs):
    out = []
    cluster = get_cluster(obj=kwargs["obj"])
    if cluster is None:
        return out

    for service in Service.objects.filter(cluster=cluster).order_by("prototype__name"):
        out.append(service.prototype.name)

    return out


def variant_service_to_add(**kwargs):
    out = []
    cluster = get_cluster(obj=kwargs["obj"])
    if cluster is None:
        return out

    for proto in (
        Prototype.objects.filter(bundle=cluster.prototype.bundle, type="service")
        .exclude(id__in=Service.objects.filter(cluster=cluster).values("prototype"))
        .order_by("name")
    ):
        out.append(proto.name)

    return out


def var_host_and(cluster, args):  # noqa: ARG001
    if not isinstance(args, list):
        err("CONFIG_VARIANT_ERROR", 'arguments of "and" predicate should be a list')

    if not args:
        return []

    return sorted(set.intersection(*[set(a) for a in args]))


def var_host_or(cluster, args):  # noqa: ARG001
    if not isinstance(args, list):
        err("CONFIG_VARIANT_ERROR", 'arguments of "or" predicate should be a list')

    if not args:
        return []

    return sorted(set.union(*[set(a) for a in args]))


def var_host_get_service(cluster, args, func):
    if "service" not in args:
        err("CONFIG_VARIANT_ERROR", f'no "service" argument for predicate "{func}"')

    return Service.objects.get(cluster=cluster, prototype__name=args["service"])


def var_host_get_component(cluster, args, service, func):
    if "component" not in args:
        err("CONFIG_VARIANT_ERROR", f'no "component" argument for predicate "{func}"')

    return Component.objects.get(cluster=cluster, service=service, prototype__name=args["component"])


@return_empty_on_not_found
def var_host_in_service(cluster, args):
    out = []
    service = var_host_get_service(cluster, args, "in_service")
    for hostcomponent in HostComponent.objects.filter(cluster=cluster, service=service).order_by("host__fqdn"):
        out.append(hostcomponent.host.fqdn)

    return out


@return_empty_on_not_found
def var_host_not_in_service(cluster, args):
    out = []
    service = var_host_get_service(cluster, args, "not_in_service")
    for host in Host.objects.filter(cluster=cluster).order_by("fqdn"):
        if HostComponent.objects.filter(cluster=cluster, service=service, host=host):
            continue

        out.append(host.fqdn)

    return out


def var_host_in_cluster(cluster, args):  # noqa: ARG001
    out = []
    for host in Host.objects.filter(cluster=cluster).order_by("fqdn"):
        out.append(host.fqdn)

    return out


@return_empty_on_not_found
def var_host_in_component(cluster, args):
    out = []
    service = var_host_get_service(cluster, args, "in_component")
    comp = var_host_get_component(cluster, args, service, "in_component")
    for hostcomponent in HostComponent.objects.filter(cluster=cluster, service=service, component=comp).order_by(
        "host__fqdn",
    ):
        out.append(hostcomponent.host.fqdn)

    return out


@return_empty_on_not_found
def var_host_not_in_component(cluster, args):
    out = []
    service = var_host_get_service(cluster, args, "not_in_component")
    comp = var_host_get_component(cluster, args, service, "not_in_component")
    for host in Host.objects.filter(cluster=cluster).order_by("fqdn"):
        if HostComponent.objects.filter(cluster=cluster, component=comp, host=host):
            continue

        out.append(host.fqdn)

    return out


def var_host_in_hc(cluster, args):  # noqa: ARG001
    out = []
    for hostcomponent in HostComponent.objects.filter(cluster=cluster).order_by("host__fqdn"):
        out.append(hostcomponent.host.fqdn)

    return out


def var_host_not_in_hc(cluster, args):  # noqa: ARG001
    out = []
    for host in Host.objects.filter(cluster=cluster).order_by("fqdn"):
        if HostComponent.objects.filter(cluster=cluster, host=host):
            continue

        out.append(host.fqdn)

    return out


def var_host_inline_list(cluster, args):  # noqa: ARG001
    return args["list"]


VARIANT_HOST_FUNC = {
    "and": var_host_and,
    "or": var_host_or,
    "in_cluster": var_host_in_cluster,
    "in_service": var_host_in_service,
    "not_in_service": var_host_not_in_service,
    "in_component": var_host_in_component,
    "not_in_component": var_host_not_in_component,
    "in_hc": var_host_in_hc,
    "not_in_hc": var_host_not_in_hc,
    "inline_list": var_host_inline_list,  # just for logic functions (and, or) test purpose
}


def var_host_solver(cluster, func_map, args):
    def check_key(key, _args):
        if not isinstance(_args, dict):
            err("CONFIG_VARIANT_ERROR", "predicate item should be a map")

        if key not in _args:
            err("CONFIG_VARIANT_ERROR", f'no "{key}" key in solver args')

    if args is None:
        return None

    if isinstance(args, dict):
        if "predicate" not in args:
            return args
        else:  # noqa: RET505
            predicate = args["predicate"]
            if predicate not in func_map:
                err("CONFIG_VARIANT_ERROR", f'no "{predicate}" in list of host functions')

            check_key("args", args)
            return func_map[predicate](cluster, var_host_solver(cluster, func_map, args["args"]))

    res = []
    if not isinstance(args, list):
        err("CONFIG_VARIANT_ERROR", "arguments of solver should be a list or a map")

    for item in args:
        check_key("predicate", item)
        check_key("args", item)
        predicate = item["predicate"]
        if predicate not in func_map:
            err("CONFIG_VARIANT_ERROR", f'no "{predicate}" in list of host functions')

        res.append(func_map[predicate](cluster, var_host_solver(cluster, func_map, item["args"])))

    return res


def variant_host(**kwargs):
    cluster = get_cluster(obj=kwargs["obj"])
    if not cluster:
        return []

    if not isinstance(kwargs["args"], dict):
        err("CONFIG_VARIANT_ERROR", "arguments of variant host function should be a map")

    if "predicate" not in kwargs["args"]:
        err("CONFIG_VARIANT_ERROR", 'no "predicate" key in variant host function arguments')

    return var_host_solver(cluster=cluster, func_map=VARIANT_HOST_FUNC, args=kwargs["args"])


def variant_host_in_cluster(**kwargs):
    out = []
    cluster = get_cluster(obj=kwargs["obj"])
    if cluster is None:
        return out

    args = kwargs["args"]
    if args and "service" in args:
        try:
            service = Service.objects.get(cluster=cluster, prototype__name=args["service"])
        except Service.DoesNotExist:
            return []

        if "component" in args:
            try:
                comp = Component.objects.get(
                    cluster=cluster,
                    service=service,
                    prototype__name=args["component"],
                )
            except Component.DoesNotExist:
                return []

            for hostcomponent in HostComponent.objects.filter(
                cluster=cluster,
                service=service,
                component=comp,
            ).order_by("host__fqdn"):
                out.append(hostcomponent.host.fqdn)

            return out
        else:  # noqa: RET505
            for hostcomponent in HostComponent.objects.filter(cluster=cluster, service=service).order_by("host__fqdn"):
                out.append(hostcomponent.host.fqdn)  # noqa: RET505

            return out

    for host in Host.objects.filter(cluster=cluster).order_by("fqdn"):
        out.append(host.fqdn)

    return out


def variant_host_not_in_clusters(**kwargs):  # noqa: ARG001
    out = []
    for host in Host.objects.filter(cluster=None).order_by("fqdn"):
        out.append(host.fqdn)

    return out


VARIANT_FUNCTIONS = {
    # function's signature MUST be ...(**kwargs)
    "host": variant_host,
    "host_in_cluster": variant_host_in_cluster,
    "host_not_in_clusters": variant_host_not_in_clusters,
    "service_in_cluster": variant_service_in_cluster,
    "service_to_add": variant_service_to_add,
}


def get_builtin_variant(obj, func_name, args):
    if func_name not in VARIANT_FUNCTIONS:
        logger.warning("unknown variant builtin function: %s", func_name)

        return None

    try:
        return VARIANT_FUNCTIONS[func_name](obj=obj, args=args)
    except AdcmEx as e:
        if e.code == "CONFIG_VARIANT_ERROR":
            return []

        raise e


def get_variant(obj, conf, limits):
    value = None
    source = limits["source"]
    if source["type"] == "config":
        name, subname, *_ = f'{source["name"]}/'.split("/")
        if not subname:
            if name in conf:
                value = conf[name]
            elif name not in conf and source["strict"]:
                raise AdcmEx(code="CONFIG_VARIANT_ERROR", msg=f"{name}/ field should be in config")
        else:
            if name in conf and subname in conf[name]:
                value = conf[name][subname]
            elif (name not in conf or subname not in conf) and source["strict"]:
                raise AdcmEx(code="CONFIG_VARIANT_ERROR", msg=f"{name}/{subname} field should be in config")

    elif source["type"] == "builtin":
        value = get_builtin_variant(obj, source["name"], source.get("args", None))
    elif source["type"] == "inline":
        value = source["value"]

    return value


def process_variant(obj, spec, conf) -> None:
    def set_variant(_spec):
        limits = _spec["limits"]
        limits["source"]["value"] = get_variant(obj, conf, limits)

        return limits

    for key in spec:
        if "type" in spec[key]:
            if spec[key]["type"] == "variant":
                spec[key]["limits"] = set_variant(spec[key])
        else:
            for subkey in spec[key]:
                if spec[key][subkey]["type"] == "variant":
                    spec[key][subkey]["limits"] = set_variant(spec[key][subkey])

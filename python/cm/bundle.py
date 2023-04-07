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

# pylint: disable=too-many-lines

import functools
import hashlib
import shutil
import tarfile
from collections.abc import Iterable
from pathlib import Path

from cm.adcm_config import init_object_config, proto_ref, switch_config
from cm.errors import raise_adcm_ex
from cm.logger import logger
from cm.models import (
    ADCM,
    Action,
    Bundle,
    Cluster,
    HostProvider,
    ProductCategory,
    Prototype,
    PrototypeConfig,
    PrototypeExport,
    PrototypeImport,
    StageAction,
    StagePrototype,
    StagePrototypeConfig,
    StagePrototypeExport,
    StagePrototypeImport,
    StageSubAction,
    StageUpgrade,
    SubAction,
    Upgrade,
)
from cm.stack import get_config_files, read_definition, save_definition
from cm.status_api import post_event
from django.conf import settings
from django.db import IntegrityError, transaction
from rbac.models import Role
from rbac.upgrade.role import prepare_action_roles
from version_utils import rpm

STAGE = (
    StagePrototype,
    StageAction,
    StagePrototypeConfig,
    StageUpgrade,
    StagePrototypeExport,
    StagePrototypeImport,
)


def load_bundle(bundle_file: str) -> None:
    logger.info('loading bundle file "%s" ...', bundle_file)
    bundle_hash, path = process_file(bundle_file=bundle_file)

    try:
        check_stage()
        process_bundle(path=path, bundle_hash=bundle_hash)
        bundle_proto = get_stage_bundle(bundle_file)
        second_pass()
    except Exception:
        clear_stage()
        shutil.rmtree(path)
        raise

    try:
        bundle = copy_stage(bundle_hash=bundle_hash, bundle_proto=bundle_proto)
        order_versions()
        clear_stage()
        ProductCategory.re_collect()
        bundle.refresh_from_db()
        prepare_action_roles(bundle=bundle)
        post_event(event="create", obj=bundle)

        return bundle
    except Exception:
        clear_stage()
        raise


def update_bundle(bundle):
    try:
        check_stage()
        process_bundle(settings.BUNDLE_DIR / bundle.hash, bundle.hash)
        get_stage_bundle(bundle.name)
        second_pass()
        update_bundle_from_stage(bundle)
        order_versions()
        clear_stage()
    except Exception:
        clear_stage()
        raise


def order_model_versions(model):
    items = []
    for obj in model.objects.all():
        items.append(obj)
    ver = ""
    count = 0
    for obj in sorted(
        items,
        key=functools.cmp_to_key(lambda obj1, obj2: rpm.compare_versions(obj1.version, obj2.version)),
    ):
        if ver != obj.version:
            count += 1
        obj.version_order = count
        ver = obj.version
    # Update all table in one time. That is much faster than one by one method
    model.objects.bulk_update(items, ["version_order"])


def order_versions():
    order_model_versions(Prototype)
    order_model_versions(Bundle)


def process_file(bundle_file: str) -> tuple[str, Path]:
    path = Path(settings.DOWNLOAD_DIR, bundle_file)
    bundle_hash = get_hash_safe(path=str(path))
    dir_path = untar_safe(bundle_hash=bundle_hash, path=path)

    return bundle_hash, dir_path


def untar_safe(bundle_hash: str, path: Path) -> Path:
    dir_path = None

    try:
        dir_path = untar(bundle_hash=bundle_hash, bundle=path)
    except tarfile.ReadError:
        raise_adcm_ex("BUNDLE_ERROR", f"Can't open bundle tar file: {path}")

    return dir_path


def untar(bundle_hash: str, bundle: Path) -> Path:
    path = Path(settings.BUNDLE_DIR, bundle_hash)
    if path.is_dir():
        try:
            existed = Bundle.objects.get(hash=bundle_hash)
            raise_adcm_ex(
                code="BUNDLE_ERROR",
                msg=f"Bundle already exists. Name: {existed.name}, "
                f"version: {existed.version}, edition: {existed.edition}",
            )
        except Bundle.DoesNotExist:
            logger.warning(
                (
                    f"There is no bundle with hash {bundle_hash} in DB, ",
                    "but there is a dir on disk with this hash. Dir will be overwritten.",
                ),
            )

    tar = tarfile.open(bundle)  # pylint: disable=consider-using-with
    tar.extractall(path=path)
    tar.close()

    return path


def get_hash_safe(path: str) -> str:
    bundle_hash = None

    try:
        bundle_hash = get_hash(path)
    except FileNotFoundError:
        raise_adcm_ex(code="BUNDLE_ERROR", msg=f"Can't find bundle file: {path}")
    except PermissionError:
        raise_adcm_ex(code="BUNDLE_ERROR", msg=f"Can't open bundle file: {path}")
    return bundle_hash


def get_hash(bundle_file: str) -> str:
    sha1 = hashlib.sha1()
    with open(bundle_file, "rb") as f:
        for data in iter(lambda: f.read(16384), b""):
            sha1.update(data)

    return sha1.hexdigest()


def load_adcm():
    check_stage()
    adcm_file = Path(settings.BASE_DIR, "conf", "adcm", "config.yaml")
    conf = read_definition(conf_file=adcm_file)
    if not conf:
        logger.warning("Empty adcm config (%s)", adcm_file)
        return

    try:
        save_definition(path=Path(""), fname=adcm_file, conf=conf, obj_list={}, bundle_hash="adcm", adcm_=True)
        process_adcm()
    except Exception:
        clear_stage()

        raise

    clear_stage()


def process_adcm():
    adcm_stage_proto = StagePrototype.objects.get(type="adcm")
    adcm = ADCM.objects.filter()
    if adcm:
        old_proto = adcm[0].prototype
        new_proto = adcm_stage_proto
        if old_proto.version == new_proto.version:
            logger.debug("adcm version %s, skip upgrade", old_proto.version)
        elif rpm.compare_versions(old_proto.version, new_proto.version) < 0:
            bundle = copy_stage("adcm", adcm_stage_proto)
            upgrade_adcm(adcm[0], bundle)
        else:
            raise_adcm_ex(
                code="UPGRADE_ERROR",
                msg=f"Current adcm version {old_proto.version} is more than "
                f"or equal to upgrade version {new_proto.version}",
            )
    else:
        bundle = copy_stage("adcm", adcm_stage_proto)
        init_adcm(bundle)


def init_adcm(bundle):
    proto = Prototype.objects.get(type="adcm", bundle=bundle)
    with transaction.atomic():
        adcm = ADCM.objects.create(prototype=proto, name="ADCM")
        obj_conf = init_object_config(proto, adcm)
        adcm.config = obj_conf
        adcm.save()

    logger.info("init adcm object version %s OK", proto.version)

    return adcm


def upgrade_adcm(adcm, bundle):
    old_proto = adcm.prototype
    new_proto = Prototype.objects.get(type="adcm", bundle=bundle)
    if rpm.compare_versions(old_proto.version, new_proto.version) >= 0:
        raise_adcm_ex(
            code="UPGRADE_ERROR",
            msg=f"Current adcm version {old_proto.version} is more than "
            f"or equal to upgrade version {new_proto.version}",
        )
    with transaction.atomic():
        adcm.prototype = new_proto
        adcm.save()
        switch_config(adcm, new_proto, old_proto)

    logger.info(
        "upgrade adcm OK from version %s to %s",
        old_proto.version,
        adcm.prototype.version,
    )

    return adcm


def process_bundle(path: Path, bundle_hash: str) -> None:
    obj_list = {}
    for conf_path, conf_file in get_config_files(path=path):
        conf = read_definition(conf_file=conf_file)
        if not conf:
            continue

        adcm_min_version = [item["adcm_min_version"] for item in conf if item.get("adcm_min_version")]
        if adcm_min_version and rpm.compare_versions(adcm_min_version[0], settings.ADCM_VERSION) > 0:
            raise_adcm_ex(
                code="BUNDLE_VERSION_ERROR",
                msg=f"This bundle required ADCM version equal to {adcm_min_version} or newer.",
            )

        save_definition(conf_path, conf_file, conf, obj_list, bundle_hash)


def check_stage():
    for model_cls in STAGE:
        if model_cls.objects.exists():
            raise_adcm_ex(code="BUNDLE_ERROR", msg=f"Stage is not empty {model_cls}")


def copy_obj(orig, clone, fields):
    obj = clone()
    for f in fields:
        setattr(obj, f, getattr(orig, f))

    return obj


def update_obj(dest, source, fields):
    for f in fields:
        setattr(dest, f, getattr(source, f))


def re_check_actions():
    for act in StageAction.objects.all():
        if not act.hostcomponentmap:
            continue

        hostcomponent = act.hostcomponentmap
        ref = f'in hc_acl of action "{act.name}" of {proto_ref(act.prototype)}'
        for item in hostcomponent:
            stage_proto = StagePrototype.objects.filter(type="service", name=item["service"]).first()
            if not stage_proto:
                raise_adcm_ex(
                    code="INVALID_ACTION_DEFINITION",
                    msg=f'Unknown service "{item["service"]}" {ref}',
                )

            if not StagePrototype.objects.filter(parent=stage_proto, type="component", name=item["component"]):
                raise_adcm_ex(
                    code="INVALID_ACTION_DEFINITION",
                    msg=f'Unknown component "{item["component"]}" of service "{stage_proto.name}" {ref}',
                )


def check_component_requires(comp):
    if not comp.requires:
        return

    req_list = comp.requires
    for i, item in enumerate(req_list):
        if "service" in item:
            service = StagePrototype.obj.get(name=item["service"], type="service")
        else:
            service = comp.parent
            req_list[i]["service"] = comp.parent.name
        req_comp = StagePrototype.obj.get(name=item["component"], type="component", parent=service)
        if comp == req_comp:
            raise_adcm_ex(
                code="COMPONENT_CONSTRAINT_ERROR",
                msg=f"Component can not require themself in requires of component "
                f'"{comp.name}" of {proto_ref(comp.parent)}',
            )

    comp.requires = req_list
    comp.save()


def check_bound_component(comp):
    if not comp.bound_to:
        return

    bind = comp.bound_to
    service = StagePrototype.obj.get(name=bind["service"], type="service")
    bind_comp = StagePrototype.obj.get(name=bind["component"], type="component", parent=service)
    if comp == bind_comp:
        raise_adcm_ex(
            code="COMPONENT_CONSTRAINT_ERROR",
            msg=f'Component can not require themself in "bound_to" of '
            f'component "{comp.name}" of {proto_ref(comp.parent)}',
        )


def re_check_components():
    for comp in StagePrototype.objects.filter(type="component"):
        check_component_requires(comp)
        check_bound_component(comp)


def check_variant_host(args, ref):
    def check_predicate(predicate, _args):
        if predicate == "in_service":
            StagePrototype.obj.get(type="service", name=_args["service"])
        elif predicate == "in_component":
            service = StagePrototype.obj.get(type="service", name=_args["service"])
            StagePrototype.obj.get(type="component", name=_args["component"], parent=service)

    if args is None:
        return

    if isinstance(args, dict):
        if "predicate" not in args:
            return

        check_predicate(args["predicate"], args["args"])
        check_variant_host(args["args"], ref)

    if isinstance(args, list):
        for i in args:
            check_predicate(i["predicate"], i["args"])
            check_variant_host(i["args"], ref)


def re_check_config():  # pylint: disable=too-many-branches # noqa: C901
    sp_service = None
    same_stage_prototype_config = None

    for stage_prototype_config in StagePrototypeConfig.objects.filter(type="variant"):
        ref = proto_ref(prototype=stage_prototype_config.prototype)
        lim = stage_prototype_config.limits

        if lim["source"]["type"] == "list":
            keys = lim["source"]["name"].split("/")
            name = keys[0]
            subname = ""
            if len(keys) > 1:
                subname = keys[1]

            same_stage_prototype_config = None
            try:
                same_stage_prototype_config = StagePrototypeConfig.objects.get(
                    prototype=stage_prototype_config.prototype,
                    name=name,
                    subname=subname,
                )
            except StagePrototypeConfig.DoesNotExist:
                raise_adcm_ex(
                    code="INVALID_CONFIG_DEFINITION",
                    msg=f'Unknown config source name "{lim["source"]["name"]}" for {ref} config '
                    f'"{stage_prototype_config.name}/{stage_prototype_config.subname}"',
                )

            if same_stage_prototype_config == stage_prototype_config:
                raise_adcm_ex(
                    code="INVALID_CONFIG_DEFINITION",
                    msg=f'Config parameter "{stage_prototype_config.name}/{stage_prototype_config.subname}" '
                    f"can not refer to itself ({ref})",
                )

        elif lim["source"]["type"] == "builtin":
            if not lim["source"]["args"]:
                continue

            if lim["source"]["name"] == "host":
                check_variant_host(
                    args=lim["source"]["args"],
                    ref=f"in source:args of {ref} config "
                    f'"{stage_prototype_config.name}/{stage_prototype_config.subname}"',
                )

            if "service" in lim["source"]["args"]:
                service = lim["source"]["args"]["service"]
                try:
                    sp_service = StagePrototype.objects.get(type="service", name=service)
                except StagePrototype.DoesNotExist:
                    raise_adcm_ex(
                        code="INVALID_CONFIG_DEFINITION",
                        msg=f'Service "{service}" in source:args of {ref} config '
                        f'"{stage_prototype_config.name}/{stage_prototype_config.subname}" does not exists',
                    )

            if "component" in lim["source"]["args"]:
                comp = lim["source"]["args"]["component"]
                if sp_service:
                    try:
                        StagePrototype.objects.get(type="component", name=comp, parent=sp_service)
                    except StagePrototype.DoesNotExist:
                        raise_adcm_ex(
                            code="INVALID_CONFIG_DEFINITION",
                            msg=f'Component "{comp}" in source:args of {ref} config '
                            f'"{stage_prototype_config.name}/{stage_prototype_config.subname}" does not exists',
                        )


def second_pass():
    re_check_actions()
    re_check_components()
    re_check_config()


def copy_stage_prototype(stage_prototypes, bundle):
    prototypes = []  # Map for stage prototype id: new prototype
    for stage_prototype in stage_prototypes:
        proto = copy_obj(
            stage_prototype,
            Prototype,
            (
                "type",
                "path",
                "name",
                "version",
                "required",
                "shared",
                "license_path",
                "license_hash",
                "monitoring",
                "display_name",
                "description",
                "adcm_min_version",
                "venv",
                "config_group_customization",
                "allow_maintenance_mode",
            ),
        )
        if proto.license_path:
            proto.license = "unaccepted"
            if check_license(proto):
                proto.license = "accepted"

        proto.bundle = bundle
        prototypes.append(proto)

    Prototype.objects.bulk_create(prototypes)


def copy_stage_upgrade(stage_upgrades, bundle):
    upgrades = []
    for stage_upgrade in stage_upgrades:
        upg = copy_obj(
            stage_upgrade,
            Upgrade,
            (
                "name",
                "description",
                "min_version",
                "max_version",
                "min_strict",
                "max_strict",
                "state_available",
                "state_on_success",
                "from_edition",
            ),
        )
        upg.bundle = bundle
        upgrades.append(upg)
        if stage_upgrade.action:
            prototype = Prototype.objects.get(name=stage_upgrade.action.prototype.name, bundle=bundle)
            upg.action = Action.objects.get(prototype=prototype, name=stage_upgrade.action.name)

    Upgrade.objects.bulk_create(upgrades)


def prepare_bulk(
    origin_objects: Iterable[StageAction] | Iterable[StagePrototypeImport],
    target: type[Action] | type[PrototypeImport],
    prototype: Prototype,
    fields: Iterable[str],
) -> list[Action] | list[PrototypeImport]:
    target_objects = []
    for origin_object in origin_objects:
        target_object = copy_obj(origin_object, target, fields)
        target_object.prototype = prototype
        target_objects.append(target_object)

    return target_objects


def copy_stage_actions(stage_actions, prototype):
    actions = prepare_bulk(
        stage_actions,
        Action,
        prototype,
        (
            "name",
            "type",
            "script",
            "script_type",
            "state_available",
            "state_unavailable",
            "state_on_success",
            "state_on_fail",
            "multi_state_available",
            "multi_state_unavailable",
            "multi_state_on_success_set",
            "multi_state_on_success_unset",
            "multi_state_on_fail_set",
            "multi_state_on_fail_unset",
            "params",
            "log_files",
            "hostcomponentmap",
            "display_name",
            "description",
            "ui_options",
            "allow_to_terminate",
            "partial_execution",
            "host_action",
            "venv",
            "allow_in_maintenance_mode",
            "config_jinja",
        ),
    )
    Action.objects.bulk_create(actions)


def copy_stage_sub_actions(bundle: Bundle) -> None:
    sub_actions = []
    for stage_sub_action in StageSubAction.objects.order_by("id"):
        if stage_sub_action.action.prototype.type == "component":
            parent = Prototype.objects.get(
                bundle=bundle,
                type="service",
                name=stage_sub_action.action.prototype.parent.name,
            )
        else:
            parent = None

        action = Action.objects.get(
            prototype__bundle=bundle,
            prototype__type=stage_sub_action.action.prototype.type,
            prototype__name=stage_sub_action.action.prototype.name,
            prototype__parent=parent,
            prototype__version=stage_sub_action.action.prototype.version,
            name=stage_sub_action.action.name,
        )
        sub_action = copy_obj(
            orig=stage_sub_action,
            clone=SubAction,
            fields=(
                "name",
                "display_name",
                "script",
                "script_type",
                "state_on_fail",
                "multi_state_on_fail_set",
                "multi_state_on_fail_unset",
                "params",
                "allow_to_terminate",
            ),
        )
        sub_action.action = action
        sub_actions.append(sub_action)

    SubAction.objects.bulk_create(sub_actions)


def copy_stage_component(stage_components, stage_proto, prototype, bundle):
    components = []

    for stage_component in stage_components:
        comp = copy_obj(
            stage_component,
            Prototype,
            (
                "type",
                "path",
                "name",
                "version",
                "required",
                "monitoring",
                "bound_to",
                "constraint",
                "requires",
                "display_name",
                "description",
                "adcm_min_version",
                "config_group_customization",
                "venv",
            ),
        )
        comp.bundle = bundle
        comp.parent = prototype
        components.append(comp)

    Prototype.objects.bulk_create(components)

    for stage_prototype in StagePrototype.objects.filter(type="component", parent=stage_proto).order_by("id"):
        proto = Prototype.objects.get(name=stage_prototype.name, type="component", parent=prototype, bundle=bundle)
        copy_stage_actions(
            stage_actions=StageAction.objects.filter(prototype=stage_prototype).order_by("id"), prototype=proto
        )
        copy_stage_config(
            stage_configs=StagePrototypeConfig.objects.filter(prototype=stage_prototype).order_by("id"),
            prototype=proto,
        )


def copy_stage_import(stage_imports, prototype):
    imports = prepare_bulk(
        stage_imports,
        PrototypeImport,
        prototype,
        (
            "name",
            "min_version",
            "max_version",
            "min_strict",
            "max_strict",
            "default",
            "required",
            "multibind",
        ),
    )
    PrototypeImport.objects.bulk_create(imports)


def copy_stage_config(stage_configs, prototype):
    target_config = []

    for stage_config in stage_configs:
        stage_config_copy = copy_obj(
            stage_config,
            PrototypeConfig,
            (
                "name",
                "subname",
                "default",
                "type",
                "description",
                "display_name",
                "limits",
                "required",
                "ui_options",
                "group_customization",
            ),
        )
        if stage_config.action:
            stage_config_copy.action = Action.objects.get(prototype=prototype, name=stage_config.action.name)

        stage_config_copy.prototype = prototype
        target_config.append(stage_config_copy)

    PrototypeConfig.objects.bulk_create(target_config)


def check_license(proto):
    return Prototype.objects.filter(license_hash=proto.license_hash, license="accepted").exists()


def copy_stage(bundle_hash, bundle_proto):
    bundle = copy_obj(
        bundle_proto,
        Bundle,
        ("name", "version", "edition", "description"),
    )
    bundle.hash = bundle_hash
    try:
        bundle.save()
    except IntegrityError:
        shutil.rmtree(settings.BUNDLE_DIR / bundle.hash)
        raise_adcm_ex(
            code="BUNDLE_ERROR",
            msg=f'Bundle "{bundle_proto.name}" {bundle_proto.version} already installed',
        )

    stage_prototypes = StagePrototype.objects.exclude(type="component").order_by("id")
    copy_stage_prototype(stage_prototypes, bundle)

    for stage_prototype in stage_prototypes:
        proto = Prototype.objects.get(name=stage_prototype.name, type=stage_prototype.type, bundle=bundle)
        copy_stage_actions(
            stage_actions=StageAction.objects.filter(prototype=stage_prototype).order_by("id"), prototype=proto
        )
        copy_stage_config(
            stage_configs=StagePrototypeConfig.objects.filter(prototype=stage_prototype).order_by("id"), prototype=proto
        )
        copy_stage_component(
            stage_components=StagePrototype.objects.filter(parent=stage_prototype, type="component").order_by("id"),
            stage_proto=stage_prototype,
            prototype=proto,
            bundle=bundle,
        )

        for stage_prototype_export in StagePrototypeExport.objects.filter(prototype=stage_prototype).order_by("id"):
            prototype_export = PrototypeExport(prototype=proto, name=stage_prototype_export.name)
            prototype_export.save()

        copy_stage_import(StagePrototypeImport.objects.filter(prototype=stage_prototype).order_by("id"), proto)

    copy_stage_sub_actions(bundle)
    copy_stage_upgrade(StageUpgrade.objects.order_by("id"), bundle)

    return bundle


def update_bundle_from_stage(  # noqa: C901
    bundle,
):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    for stage_prototype in StagePrototype.objects.all():
        try:
            prototype = Prototype.objects.get(
                bundle=bundle,
                type=stage_prototype.type,
                name=stage_prototype.name,
                version=stage_prototype.version,
            )
            prototype.path = stage_prototype.path
            prototype.version = stage_prototype.version
            prototype.description = stage_prototype.description
            prototype.display_name = stage_prototype.display_name
            prototype.required = stage_prototype.required
            prototype.shared = stage_prototype.shared
            prototype.monitoring = stage_prototype.monitoring
            prototype.adcm_min_version = stage_prototype.adcm_min_version
            prototype.venv = stage_prototype.venv
            prototype.config_group_customization = stage_prototype.config_group_customization
            prototype.allow_maintenance_mode = stage_prototype.allow_maintenance_mode
        except Prototype.DoesNotExist:
            prototype = copy_obj(
                stage_prototype,
                Prototype,
                (
                    "type",
                    "path",
                    "name",
                    "version",
                    "required",
                    "shared",
                    "monitoring",
                    "bound_to",
                    "constraint",
                    "requires",
                    "display_name",
                    "description",
                    "adcm_min_version",
                    "venv",
                    "config_group_customization",
                    "allow_maintenance_mode",
                ),
            )
            prototype.bundle = bundle

        prototype.save()
        for saction in StageAction.objects.filter(prototype=stage_prototype):
            try:
                action = Action.objects.get(prototype=prototype, name=saction.name)
                update_obj(
                    action,
                    saction,
                    (
                        "type",
                        "script",
                        "script_type",
                        "state_available",
                        "state_on_success",
                        "state_on_fail",
                        "multi_state_available",
                        "multi_state_on_success_set",
                        "multi_state_on_success_unset",
                        "multi_state_on_fail_set",
                        "multi_state_on_fail_unset",
                        "params",
                        "log_files",
                        "hostcomponentmap",
                        "display_name",
                        "description",
                        "ui_options",
                        "allow_to_terminate",
                        "partial_execution",
                        "host_action",
                        "venv",
                        "allow_in_maintenance_mode",
                    ),
                )
            except Action.DoesNotExist:
                action = copy_obj(
                    saction,
                    Action,
                    (
                        "name",
                        "type",
                        "script",
                        "script_type",
                        "state_available",
                        "state_on_success",
                        "state_on_fail",
                        "multi_state_available",
                        "multi_state_on_success_set",
                        "multi_state_on_success_unset",
                        "multi_state_on_fail_set",
                        "multi_state_on_fail_unset",
                        "params",
                        "log_files",
                        "hostcomponentmap",
                        "display_name",
                        "description",
                        "ui_options",
                        "allow_to_terminate",
                        "partial_execution",
                        "host_action",
                        "venv",
                        "allow_in_maintenance_mode",
                    ),
                )
                action.prototype = prototype

            action.save()

            SubAction.objects.filter(action=action).delete()
            for ssubaction in StageSubAction.objects.filter(action=saction):
                sub = copy_obj(
                    ssubaction,
                    SubAction,
                    (
                        "script",
                        "script_type",
                        "state_on_fail",
                        "multi_state_on_fail_set",
                        "multi_state_on_fail_unset",
                        "params",
                    ),
                )
                sub.action = action
                sub.save()

        for stage_prototype_config in StagePrototypeConfig.objects.filter(prototype=stage_prototype):
            flist = (
                "default",
                "type",
                "description",
                "display_name",
                "limits",
                "required",
                "ui_options",
                "group_customization",
            )
            act = None
            if stage_prototype_config.action:
                act = Action.objects.get(prototype=prototype, name=stage_prototype_config.action.name)

            try:
                pconfig = PrototypeConfig.objects.get(
                    prototype=prototype,
                    action=act,
                    name=stage_prototype_config.name,
                    subname=stage_prototype_config.subname,
                )
                update_obj(pconfig, stage_prototype_config, flist)
            except PrototypeConfig.DoesNotExist:
                pconfig = copy_obj(stage_prototype_config, PrototypeConfig, ("name", "subname") + flist)
                pconfig.action = act
                pconfig.prototype = prototype

            pconfig.save()

        PrototypeExport.objects.filter(prototype=prototype).delete()
        for stage_prototype_export in StagePrototypeExport.objects.filter(prototype=stage_prototype):
            prototype_export = PrototypeExport(prototype=prototype, name=stage_prototype_export.name)
            prototype_export.save()

        PrototypeImport.objects.filter(prototype=prototype).delete()
        for stage_prototype_import in StagePrototypeImport.objects.filter(prototype=stage_prototype):
            prototype_import = copy_obj(
                stage_prototype_import,
                PrototypeImport,
                (
                    "name",
                    "min_version",
                    "max_version",
                    "min_strict",
                    "max_strict",
                    "default",
                    "required",
                    "multibind",
                ),
            )
            prototype_import.prototype = prototype
            prototype_import.save()

    Upgrade.objects.filter(bundle=bundle).delete()
    for stage_upgrade in StageUpgrade.objects.all():
        upg = copy_obj(
            stage_upgrade,
            Upgrade,
            (
                "name",
                "description",
                "min_version",
                "max_version",
                "min_strict",
                "max_strict",
                "state_available",
                "state_on_success",
                "from_edition",
            ),
        )
        upg.bundle = bundle
        upg.save()


def clear_stage():
    for model in STAGE:
        model.objects.all().delete()


def delete_bundle(bundle):
    providers = HostProvider.objects.filter(prototype__bundle=bundle)
    if providers:
        provider = providers[0]
        raise_adcm_ex(
            code="BUNDLE_CONFLICT",
            msg=f'There is provider #{provider.id} "{provider.name}" of bundle '
            f'#{bundle.id} "{bundle.name}" {bundle.version}',
        )

    clusters = Cluster.objects.filter(prototype__bundle=bundle)
    if clusters:
        cluster = clusters[0]
        raise_adcm_ex(
            code="BUNDLE_CONFLICT",
            msg=f'There is cluster #{cluster.id} "{cluster.name}" '
            f'of bundle #{bundle.id} "{bundle.name}" {bundle.version}',
        )

    adcm = ADCM.objects.filter(prototype__bundle=bundle)
    if adcm:
        raise_adcm_ex(
            code="BUNDLE_CONFLICT",
            msg=f'There is adcm object of bundle #{bundle.id} "{bundle.name}" {bundle.version}',
        )
    if bundle.hash != "adcm":
        try:
            shutil.rmtree(Path(settings.BUNDLE_DIR, bundle.hash))
        except FileNotFoundError:
            logger.info(
                "Bundle %s %s was removed in file system. Delete bundle in database",
                bundle.name,
                bundle.version,
            )

    post_event(event="delete", obj=bundle)
    bundle.delete()

    for role in Role.objects.filter(class_name="ParentRole"):
        if not role.child.all():
            role.delete()

    ProductCategory.re_collect()


def check_services():
    prototype_data = {}
    for prototype in StagePrototype.objects.filter(type="service"):
        if prototype.name in prototype_data:
            raise_adcm_ex(code="BUNDLE_ERROR", msg=f"There are more than one service with name {prototype.name}")

        prototype_data[prototype.name] = prototype.version


def get_stage_bundle(bundle_file):
    bundle = None
    clusters = StagePrototype.objects.filter(type="cluster")
    providers = StagePrototype.objects.filter(type="provider")
    if clusters:
        if len(clusters) > 1:
            raise_adcm_ex(
                code="BUNDLE_ERROR",
                msg=f'There are more than one ({len(clusters)}) cluster definition in bundle "{bundle_file}"',
            )
        if providers:
            raise_adcm_ex(
                code="BUNDLE_ERROR",
                msg=f'There are {len(providers)} host provider definition in cluster type bundle "{bundle_file}"',
            )
        hosts = StagePrototype.objects.filter(type="host")
        if hosts:
            raise_adcm_ex(
                code="BUNDLE_ERROR",
                msg=f'There are {len(hosts)} host definition in cluster type bundle "{bundle_file}"',
            )
        check_services()
        bundle = clusters[0]

    elif providers:
        if len(providers) > 1:
            raise_adcm_ex(
                code="BUNDLE_ERROR",
                msg=f'There are more than one ({len(providers)}) host provider definition in bundle "{bundle_file}"',
            )
        services = StagePrototype.objects.filter(type="service")
        if services:
            raise_adcm_ex(
                code="BUNDLE_ERROR",
                msg=f'There are {len(services)} service definition in host provider type bundle "{bundle_file}"',
            )
        hosts = StagePrototype.objects.filter(type="host")
        if not hosts:
            raise_adcm_ex(
                code="BUNDLE_ERROR",
                msg=f'There isn\'t any host definition in host provider type bundle "{bundle_file}"',
            )
        bundle = providers[0]
    else:
        raise_adcm_ex(
            code="BUNDLE_ERROR",
            msg=f'There isn\'t any cluster or host provider definition in bundle "{bundle_file}"',
        )

    return bundle

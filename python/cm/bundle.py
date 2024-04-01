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

from collections.abc import Iterable
from pathlib import Path
import os
import shutil
import hashlib
import tarfile
import functools

from adcm_version import compare_adcm_versions, compare_prototype_versions
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.transaction import atomic
from gnupg import GPG, ImportResult
from rbac.models import Role
from rbac.upgrade.role import prepare_action_roles

from cm.adcm_config.config import init_object_config, switch_config
from cm.adcm_config.utils import cook_file_type_name, proto_ref
from cm.errors import AdcmEx, raise_adcm_ex
from cm.logger import logger
from cm.models import (
    ADCM,
    Action,
    Bundle,
    Cluster,
    ConfigLog,
    HostProvider,
    ObjectType,
    ProductCategory,
    Prototype,
    PrototypeConfig,
    PrototypeExport,
    PrototypeImport,
    SignatureStatus,
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

STAGE = (
    StagePrototype,
    StageAction,
    StagePrototypeConfig,
    StageUpgrade,
    StagePrototypeExport,
    StagePrototypeImport,
)


def prepare_bundle(
    bundle_file: str, bundle_hash: str, path: Path, verification_status: SignatureStatus = SignatureStatus.ABSENT
) -> Bundle:
    try:
        check_stage()
        prototypes, upgrades = process_bundle(path=path, bundle_hash=bundle_hash)
        bundle_prototype = get_stage_bundle(bundle_file=bundle_file)
        check_services_requires()
        re_check_actions()
        re_check_components()
        re_check_config()

        bundle = copy_stage(
            bundle_hash=bundle_hash, bundle_proto=bundle_prototype, verification_status=verification_status
        )
        order_versions()

        ProductCategory.re_collect()
        bundle.refresh_from_db()
        prepare_action_roles(bundle=bundle)

        StagePrototype.objects.filter(id__in=[prototype.id for prototype in prototypes]).delete()
        StageUpgrade.objects.filter(id__in=[upgrade.id for upgrade in upgrades]).delete()

        return bundle

    except Exception as error:
        shutil.rmtree(path, ignore_errors=True)
        raise error


def load_bundle(bundle_file: str) -> Bundle:
    logger.info('loading bundle file "%s" ...', bundle_file)
    bundle_hash, path = process_file(bundle_file=bundle_file)

    bundle_archive, signature_file = get_bundle_and_signature_paths(path=path)
    verification_status = get_verification_status(bundle_archive=bundle_archive, signature_file=signature_file)
    untar_and_cleanup(bundle_archive=bundle_archive, signature_file=signature_file, bundle_hash=bundle_hash)

    with atomic():
        return prepare_bundle(
            bundle_file=bundle_file, bundle_hash=bundle_hash, path=path, verification_status=verification_status
        )


def get_bundle_and_signature_paths(path: Path) -> tuple[Path | None, Path | None]:
    """
    Search for tarfile (actual bundle archive), `.sig` file (detached signature file)
    This paths can be None when processing old style bundles
    """

    bundle_archive, signature_file = None, None

    for item in path.glob("*"):
        if item.match("*.sig"):
            if signature_file is not None:
                raise AdcmEx(code="BUNDLE_ERROR", msg='More than one ".sig" file found')
            signature_file = item.absolute()
            continue

        if item.is_file() and tarfile.is_tarfile(item):
            if bundle_archive is not None:
                raise AdcmEx(code="BUNDLE_ERROR", msg="More than one tar file found")
            bundle_archive = item.absolute()
            continue

    return bundle_archive, signature_file


def untar_and_cleanup(bundle_archive: Path | None, signature_file: Path | None, bundle_hash: str) -> None:
    if bundle_archive is not None:
        untar_safe(bundle_hash=bundle_hash, path=bundle_archive)
        bundle_archive.unlink()
    if signature_file is not None:
        signature_file.unlink()


def get_verification_status(bundle_archive: Path | None, signature_file: Path | None) -> SignatureStatus:
    if bundle_archive is None or signature_file is None:
        return SignatureStatus.ABSENT

    gpg = GPG(gpgbinary=os.popen("which gpg").read().strip())  # noqa: S605, S607
    gpg.encoding = settings.ENCODING_UTF_8
    key_filepath = cook_file_type_name(obj=ADCM.objects.get(), key="global", sub_key="verification_public_key")

    try:
        res: ImportResult = gpg.import_keys_file(key_path=key_filepath)
    except (PermissionError, FileNotFoundError):
        logger.warning("Can't read public key file: %s", key_filepath)
        return SignatureStatus.INVALID

    if res.returncode != 0:
        logger.warning("Bad gpg key: %s", res.stderr)
        return SignatureStatus.INVALID

    with open(signature_file, mode="rb") as sign_stream:
        if bool(gpg.verify_file(fileobj_or_path=sign_stream, data_filename=bundle_archive)):
            return SignatureStatus.VALID
        else:
            return SignatureStatus.INVALID


def upload_file(file) -> Path:
    file_path = Path(settings.DOWNLOAD_DIR, file.name)
    with open(file_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)

    return file_path


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
    for obj in model.objects.order_by("id"):
        items.append(obj)
    ver = ""
    count = 0
    for obj in sorted(
        items,
        key=functools.cmp_to_key(lambda obj1, obj2: compare_prototype_versions(obj1.version, obj2.version)),
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
        raise_adcm_ex(code="BUNDLE_ERROR", msg=f"Can't open bundle tar file: {path}")

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

    tar = tarfile.open(bundle)  # noqa: SIM115
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
    sha1 = hashlib.sha1()  # noqa: S324
    with open(bundle_file, "rb") as f:
        for data in iter(lambda: f.read(16384), b""):
            sha1.update(data)

    return sha1.hexdigest()


def load_adcm(adcm_file: Path = Path(settings.BASE_DIR, "conf", "adcm", "config.yaml")):
    check_stage()
    conf = read_definition(conf_file=adcm_file)

    if not conf:
        logger.warning("Empty adcm config (%s)", adcm_file)
        return

    with atomic():
        prototypes, _ = save_definition(
            path=Path(), fname=adcm_file, conf=conf, obj_list={}, bundle_hash="adcm", adcm_=True
        )
        process_adcm()
        StagePrototype.objects.filter(id__in=[prototype.id for prototype in prototypes]).delete()


def process_adcm():
    adcm_stage_proto = StagePrototype.objects.get(type="adcm")
    adcm = ADCM.objects.first()

    if adcm:
        old_proto = adcm.prototype
        new_proto = adcm_stage_proto

        if old_proto.version == new_proto.version:
            logger.debug("adcm version %s, skip upgrade", old_proto.version)
        elif compare_prototype_versions(old_proto.version, new_proto.version) < 0:
            bundle = copy_stage("adcm", adcm_stage_proto)
            upgrade_adcm(adcm, bundle)
        else:
            raise AdcmEx(
                code="UPGRADE_ERROR",
                msg=(
                    f"Current adcm version {old_proto.version} is more than "
                    f"or equal to upgrade version {new_proto.version}"
                ),
            )
    else:
        bundle = copy_stage("adcm", adcm_stage_proto)
        init_adcm(bundle)


def set_adcm_url(adcm: ADCM) -> None:
    adcm_url = os.getenv("DEFAULT_ADCM_URL")

    if adcm_url is None:
        return

    config_log = ConfigLog.objects.filter(id=adcm.config.current).first()
    config_log.config["global"]["adcm_url"] = adcm_url
    config_log.save(update_fields=["config"])
    logger.info("Set ADCM's URL from environment variable: %s", adcm_url)


def init_adcm(bundle: Bundle) -> ADCM:
    proto = Prototype.objects.get(type="adcm", bundle=bundle)

    with transaction.atomic():
        adcm = ADCM.objects.create(prototype=proto, name="ADCM")
        adcm.config = init_object_config(proto, adcm)
        adcm.save(update_fields=["config"])

    set_adcm_url(adcm=adcm)

    logger.info("init adcm object version %s OK", proto.version)

    return adcm


def upgrade_adcm(adcm, bundle):
    old_proto = adcm.prototype
    new_proto = Prototype.objects.get(type="adcm", bundle=bundle)
    if compare_prototype_versions(old_proto.version, new_proto.version) >= 0:
        raise_adcm_ex(
            code="UPGRADE_ERROR",
            msg=f"Current adcm version {old_proto.version} is more than "
            f"or equal to upgrade version {new_proto.version}",
        )
    with transaction.atomic():
        adcm.prototype = new_proto
        adcm.save()
        switch_config(adcm, new_proto, old_proto)

        if (
            compare_prototype_versions(old_proto.version, "2.6")
            <= 0
            <= compare_prototype_versions(new_proto.version, "2.7")
        ):
            config_log_old = ConfigLog.objects.get(obj_ref=adcm.config, id=adcm.config.previous)
            config_log_new = ConfigLog.objects.get(obj_ref=adcm.config, id=adcm.config.current)
            log_rotation_on_fs = config_log_old.config.get("job_log", {}).get(
                "log_rotation_on_fs", config_log_new.config["audit_data_retention"]["log_rotation_on_fs"]
            )
            config_log_new.config["audit_data_retention"]["log_rotation_on_fs"] = log_rotation_on_fs

            log_rotation_in_db = config_log_old.config.get("job_log", {}).get(
                "log_rotation_in_db", config_log_new.config["audit_data_retention"]["log_rotation_in_db"]
            )
            config_log_new.config["audit_data_retention"]["log_rotation_in_db"] = log_rotation_in_db

            config_rotation_in_db = config_log_old.config.get("config_rotation", {}).get(
                "config_rotation_in_db", config_log_new.config["audit_data_retention"]["config_rotation_in_db"]
            )
            config_log_new.config["audit_data_retention"]["config_rotation_in_db"] = config_rotation_in_db

            config_log_new.save(update_fields=["config"])

    logger.info(
        "upgrade adcm OK from version %s to %s",
        old_proto.version,
        adcm.prototype.version,
    )

    return adcm


def check_adcm_min_version(adcm_min_version: str) -> None:
    if compare_adcm_versions(adcm_min_version, settings.ADCM_VERSION) > 0:
        raise AdcmEx(
            code="BUNDLE_VERSION_ERROR",
            msg=f"This bundle required ADCM version equal to {adcm_min_version} or newer.",
        )


def process_bundle(path: Path, bundle_hash: str) -> tuple[list[StagePrototype], list[StageUpgrade]]:
    all_prototypes = []
    all_upgrades = []
    obj_list = {}
    for conf_path, conf_file in get_config_files(path=path):
        conf = read_definition(conf_file=conf_file)
        if not conf:
            continue

        for item in conf:
            if "adcm_min_version" in item:
                check_adcm_min_version(adcm_min_version=item["adcm_min_version"])

        prototypes, upgrades = save_definition(conf_path, conf_file, conf, obj_list, bundle_hash)
        all_prototypes.extend(prototypes)
        all_upgrades.extend(upgrades)

    return all_prototypes, all_upgrades


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


def re_check_actions() -> None:
    for action in StageAction.objects.select_related("prototype").order_by("id"):
        if not action.hostcomponentmap:
            continue

        ref = f'in hc_acl of action "{action.name}" of {proto_ref(action.prototype)}'

        for item in action.hostcomponentmap:
            if action.prototype.type != "service" and "service" not in item:
                raise_adcm_ex(code="INVALID_ACTION_DEFINITION", msg=f'"service" filed is required {ref}')

            prototype = StagePrototype.objects.filter(type="service", name=item["service"]).first()
            if not prototype:
                raise_adcm_ex(
                    code="INVALID_ACTION_DEFINITION",
                    msg=f'Unknown service "{item["service"]}" {ref}',
                )

            if not StagePrototype.objects.filter(parent=prototype, type="component", name=item["component"]).exists():
                raise_adcm_ex(
                    code="INVALID_ACTION_DEFINITION",
                    msg=f'Unknown component "{item["component"]}" of service "{prototype.name}" {ref}',
                )


def check_component_requires(comp: StagePrototype) -> None:
    if not comp.requires:
        return

    req_list = comp.requires
    for i, item in enumerate(req_list):
        req_comp = None
        if "service" in item:
            service = StagePrototype.obj.get(name=item["service"], type="service")
        else:
            service = comp.parent
            req_list[i]["service"] = comp.parent.name

        if "component" in item:
            req_comp = StagePrototype.obj.get(name=item["component"], type="component", parent=service)

        if req_comp and comp == req_comp:
            raise_adcm_ex(
                code="REQUIRES_ERROR",
                msg=f"Component can not require themself in requires of component "
                f'"{comp.name}" of {proto_ref(comp.parent)}',
            )

    comp.requires = req_list
    comp.save()


def check_services_requires() -> None:
    for service in StagePrototype.objects.filter(type="service"):
        if not service.requires:
            continue

        req_list = service.requires
        for item in req_list:
            req_service = StagePrototype.obj.get(name=item["service"], type="service")

            if service == req_service:
                raise_adcm_ex(
                    code="REQUIRES_ERROR",
                    msg=f'Service can not require themself "{service.name}" of {proto_ref(prototype=service.parent)}',
                )

            if (
                "component" in item
                and not StagePrototype.objects.filter(
                    name=item["component"],
                    parent__name=item["service"],
                    type=ObjectType.COMPONENT,
                    parent__type=ObjectType.SERVICE,
                ).exists()
            ):
                raise AdcmEx(
                    code="REQUIRES_ERROR",
                    msg=f'No required component "{item["component"]}" of service "{item["service"]}"',
                )

        service.requires = req_list
        service.save(update_fields=["requires"])


def check_bound_component(comp: StagePrototype) -> None:
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


def re_check_components() -> None:
    for comp in StagePrototype.objects.filter(type="component"):
        check_component_requires(comp=comp)
        check_bound_component(comp=comp)


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


def re_check_config() -> None:
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
    check_services_requires()
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
                "requires",
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
                "allow_flags",
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
                "display_name",
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
                "allow_flags",
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


def copy_stage(bundle_hash: str, bundle_proto, verification_status: SignatureStatus = SignatureStatus.ABSENT) -> Bundle:
    bundle = copy_obj(
        bundle_proto,
        Bundle,
        ("name", "version", "edition", "description"),
    )
    bundle.hash = bundle_hash
    bundle.signature_status = verification_status

    try:
        bundle.save()
    except IntegrityError:
        shutil.rmtree(settings.BUNDLE_DIR / bundle.hash)
        raise_adcm_ex(
            code="BUNDLE_ERROR",
            msg=f'Bundle "{bundle_proto.name}" {bundle_proto.version} already installed',
        )

    stage_prototypes = StagePrototype.objects.exclude(type="component").order_by("id")
    copy_stage_prototype(stage_prototypes=stage_prototypes, bundle=bundle)

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

        copy_stage_import(
            stage_imports=StagePrototypeImport.objects.filter(prototype=stage_prototype).order_by("id"), prototype=proto
        )

    copy_stage_sub_actions(bundle=bundle)
    copy_stage_upgrade(stage_upgrades=StageUpgrade.objects.order_by("id"), bundle=bundle)

    return bundle


def update_bundle_from_stage(
    bundle,
):
    for stage_prototype in StagePrototype.objects.order_by("id"):
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
            prototype.allow_flags = stage_prototype.allow_flags
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
                    "allow_flags",
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
    for stage_upgrade in StageUpgrade.objects.order_by("id"):
        upg = copy_obj(
            stage_upgrade,
            Upgrade,
            (
                "name",
                "display_name",
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

    bundle.delete()

    for role in Role.objects.filter(class_name="ParentRole"):
        if not role.child.order_by("id"):
            role.delete()

    ProductCategory.re_collect()


def check_services():
    prototype_data = {}
    for prototype in StagePrototype.objects.filter(type="service"):
        if prototype.name in prototype_data:
            raise_adcm_ex(code="BUNDLE_ERROR", msg=f"There are more than one service with name {prototype.name}")

        prototype_data[prototype.name] = prototype.version


def get_stage_bundle(bundle_file: str) -> StagePrototype:
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

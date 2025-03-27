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

from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from operator import methodcaller
from pathlib import Path
from tempfile import gettempdir
from typing import NamedTuple
import os
import fcntl
import shutil
import logging
import tarfile

from core.bundle_alt._config import check_default_values
from core.bundle_alt.bundle_load import get_hash_safe, untar_safe
from core.bundle_alt.convertion import extract_config
from core.bundle_alt.errors import convert_validation_to_bundle_error
from core.bundle_alt.process import ConfigJinjaContext, retrieve_bundle_definitions
from core.bundle_alt.schema import ConfigJinjaSchema
from django.conf import settings
from django.core.files import File
from django.db.transaction import atomic
from gnupg import GPG, ImportResult
from rbac.upgrade.role import prepare_action_roles
import ruyaml

from cm.errors import AdcmEx
from cm.models import ADCM, Bundle, PrototypeConfig, SignatureStatus
from cm.services.bundle_alt import repo
from cm.services.bundle_alt.errors import convert_bundle_errors_to_adcm_ex

logger = logging.getLogger("adcm")

# Dependencies


@cache
def _get_rules_for_yspec_schema():
    # COPIED
    with (settings.CODE_DIR / "cm" / "yspec_schema.yaml").open(encoding="utf-8") as f:
        return ruyaml.round_trip_load(stream=f)


# Use case


class Directories(NamedTuple):
    downloads: Path
    bundles: Path
    files: Path


def parse_bundle_from_request_to_db(
    file_from_request: File, *, directories: Directories, adcm_version: str, verified_signature_only: bool
) -> Bundle:
    archive_in_downloads = save_bundle_file_from_request_to_downloads(file_from_request=file_from_request)
    return parse_bundle_archive(
        archive=archive_in_downloads,
        directories=directories,
        adcm_version=adcm_version,
        verified_signature_only=verified_signature_only,
    )


@convert_bundle_errors_to_adcm_ex
def parse_bundle_archive(archive: Path, directories: Directories, adcm_version: str, verified_signature_only: bool):
    # Thou it's a bit of strange to remove archive in here,
    # but it's the original process,
    # required by upload-load separation in v1
    with _cleanup_on_fail(archive):
        return process_bundle_from_archive(
            archive=archive,
            bundles_dir=directories.bundles,
            files_dir=directories.files,
            adcm_version=adcm_version,
            verified_signature_only=verified_signature_only,
        )


@convert_validation_to_bundle_error
def parse_config_jinja(data: list[dict], context: ConfigJinjaContext, *, action, prototype) -> list[PrototypeConfig]:
    config = ConfigJinjaSchema.model_validate({"config": data}, strict=True)
    config = config.model_dump(exclude_unset=True, exclude_defaults=True)["config"]

    definition = extract_config(config=config, context=context)

    if not definition:
        return []

    check_default_values(
        parameters=definition.parameters, values=definition.default_values, attributes=definition.default_attrs
    )

    orm_entries = repo.convert_config_definition_to_orm_model(definition=definition, prototype=prototype, action=action)

    return list(orm_entries)


# Public


@convert_bundle_errors_to_adcm_ex
def save_bundle_file_from_request_to_downloads(file_from_request: File) -> Path:
    archive_in_tmp = _write_bundle_archive_to_tempdir(file_from_request=file_from_request)
    return _safe_copy_to_downloads(archive=archive_in_tmp)


def process_bundle_from_archive(
    archive: Path, bundles_dir: Path, files_dir: Path, adcm_version: str, verified_signature_only: bool
) -> Bundle:
    """Unpack bundle to bundles dir, read definitions, create bundle"""
    bundle_hash = get_hash_safe(archive)
    unpacking_info = _unpack_bundle(
        archive=archive, bundles_dir=bundles_dir, bundle_hash=bundle_hash, files_dir=files_dir
    )

    with _cleanup_on_fail(unpacking_info.root):
        _verify_signature(unpacking_info.signature, verified_signature_only)
        # yaml spec probably should be external dependency
        definitions = retrieve_bundle_definitions(
            bundle_dir=unpacking_info.root, adcm_version=adcm_version, yspec_schema=_get_rules_for_yspec_schema()
        )

        with atomic():
            bundle = repo.save_definitions(
                bundle_definitions=definitions,
                bundle_root=unpacking_info.root,
                bundle_hash=unpacking_info.hash,
                verification_status=unpacking_info.signature,
            )
            repo.order_versions()
            repo.recollect_categories()
            bundle.refresh_from_db()
            prepare_action_roles(bundle=bundle)

    return bundle


# Steps


@dataclass(slots=True)
class _BundleUnpackingInfo:
    hash: str
    root: Path
    signature: SignatureStatus = SignatureStatus.ABSENT


def _unpack_bundle(archive: Path, bundles_dir: Path, bundle_hash: str, files_dir: Path) -> _BundleUnpackingInfo:
    info = _BundleUnpackingInfo(hash=bundle_hash, root=bundles_dir / bundle_hash)

    if info.root.is_dir():
        bundle = repo.find_bundle_by_hash(info.hash)
        if bundle:
            raise AdcmEx(
                code="BUNDLE_ERROR",
                msg=f"Bundle already exists. Name: {bundle.name}, "
                f"version: {bundle.version}, edition: {bundle.edition}",
            )

        logger.warning(
            f"There is no bundle with hash {info.hash} in DB, "
            "but there is a dir on disk with this hash. Dir will be overwritten.",
        )

    untar_safe(to=info.root, tar_from=archive)

    inner_bundle_archive = _find_inner_archive(info.root)

    signature_file = _find_signature_file(info.root)
    if signature_file:
        if inner_bundle_archive:
            info.signature = _calculate_bundle_verification_status(
                bundle_archive=inner_bundle_archive, signature_file=signature_file, files_dir=files_dir
            )

        signature_file.unlink()

    if inner_bundle_archive:
        untar_safe(to=info.root, tar_from=inner_bundle_archive)
        inner_bundle_archive.unlink()

    return info


def _calculate_bundle_verification_status(
    bundle_archive: Path, signature_file: Path, files_dir: Path
) -> SignatureStatus:
    # TAKEN FROM cm.bundle.get_verification_status
    gpg = GPG(gpgbinary=os.popen("which gpg").read().strip())  # noqa: S605, S607
    gpg.encoding = "utf-8"
    # TODO raw taken from "cook_file_type_name", but there should be an alternative way
    #  ALSO find a way to avoid requesting ADCM ID
    #  MAYBE make it a cached function?
    adcm_id = ADCM.objects.values_list("id", flat=True).get()
    key_filepath = files_dir / "adcm" / str(adcm_id) / "global" / "verification_public_key"

    try:
        res: ImportResult = gpg.import_keys_file(key_path=key_filepath)
    except (PermissionError, FileNotFoundError):
        logger.warning("Can't read public key file: %s", key_filepath)
        return SignatureStatus.INVALID

    if res.returncode != 0:
        logger.warning("Bad gpg key: %s", res.stderr)
        return SignatureStatus.INVALID

    with open(signature_file, mode="rb") as sign_stream:
        if bool(gpg.verify_file(fileobj_or_path=sign_stream, data_filename=str(bundle_archive))):
            return SignatureStatus.VALID

        return SignatureStatus.INVALID


# Utils


@contextmanager
def _upload_fs_lock():
    with Path(gettempdir(), "upload.lock").open(mode="w") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _find_duplicate(archive: Path, in_: Path) -> Path | None:
    archive_hash = get_hash_safe(path=archive)
    existing_files = filter(methodcaller("is_file"), in_.iterdir())
    for file_ in existing_files:
        file_hash = get_hash_safe(file_)
        if archive_hash == file_hash:
            return file_

    return None


def _find_inner_archive(directory: Path) -> Path | None:
    files_in_dir = filter(methodcaller("is_file"), directory.iterdir())
    tarfiles = tuple(filter(tarfile.is_tarfile, files_in_dir))

    if not tarfiles:
        return None

    if len(tarfiles) == 1:
        return tarfiles[0].absolute()

    raise AdcmEx(code="BUNDLE_ERROR", msg="More than one tar file found")


def _find_signature_file(directory: Path) -> Path | None:
    signature_files = tuple(directory.glob("*.sig"))

    if not signature_files:
        return None

    if len(signature_files) == 1:
        return signature_files[0].absolute()

    raise AdcmEx(code="BUNDLE_ERROR", msg='More than one ".sig" file found')


@contextmanager
def _cleanup_on_fail(*paths: Path):
    try:
        yield
    except Exception:
        for path in paths:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                logger.warning(f"Path assigned for cleanup on error, but it's neither existing file or dir: {path}")

        raise


def _verify_signature(bundle_signature: SignatureStatus, verified_signature_only: bool) -> None:
    if bundle_signature != SignatureStatus.VALID and verified_signature_only:
        raise AdcmEx(
            code="BUNDLE_SIGNATURE_VERIFICATION_ERROR",
            msg=(f"Upload rejected due to failed bundle verification: bundle's signature is '{bundle_signature}'"),
        )


def _write_bundle_archive_to_tempdir(file_from_request: File) -> Path:
    """Save file from request to tempdir, so it can be processed further"""
    tmp_path = Path(gettempdir(), str(file_from_request.name))

    with tmp_path.open(mode="wb+") as f:
        for chunk in file_from_request.chunks():
            f.write(chunk)

    return tmp_path


def _safe_copy_to_downloads(archive: Path, downloads_dir: Path = settings.DOWNLOAD_DIR) -> Path:
    """Copy file to downloads dir if there isn't already archive with such content"""
    target_path = downloads_dir / archive.name

    with _upload_fs_lock():
        existing_file = _find_duplicate(archive, in_=downloads_dir)
        if existing_file:
            message = f"Bundle already exists: Bundle with the same content is already uploaded {existing_file}"
            raise AdcmEx(code="BUNDLE_ERROR", msg=message)

        # move to downloads
        shutil.move(src=archive, dst=target_path)

        return target_path

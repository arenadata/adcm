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
from contextlib import contextmanager
from operator import methodcaller
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir
from typing import Protocol
import os
import fcntl
import shutil
import logging
import tarfile

from gnupg import GPG

from core.bundle._errors import BundleParsingError, BundleProcessingError, BundleSignatureVerificationError
from core.bundle._files import get_hash_safe, untar_safe
from core.bundle._repo import BundleRepoI
from core.bundle._types import BundleUnpackingInfo, SignatureStatus

logger = logging.getLogger("adcm")


class UploadedFileLike(Protocol):
    name: str

    def chunks(self) -> Iterable[bytes]:
        ...


# Public


def save_bundle_file_from_request_to_downloads(file_from_request: UploadedFileLike, downloads_dir: Path) -> Path:
    archive_in_tmp = _write_bundle_archive_to_tempdir(file_from_request=file_from_request)
    return _safe_copy_to_downloads(archive=archive_in_tmp, downloads_dir=downloads_dir)


# Steps


def unpack_bundle(archive: Path, bundles_dir: Path, files_dir: Path, repo: BundleRepoI) -> BundleUnpackingInfo:
    bundle_hash = get_hash_safe(archive)
    info = BundleUnpackingInfo(hash=bundle_hash, root=bundles_dir / bundle_hash)

    if info.root.is_dir():
        existing = repo.find_existing_bundle(info.hash)
        if existing:
            raise BundleProcessingError(
                f"Bundle already exists. Name: {existing.name}, "
                f"version: {existing.version}, edition: {existing.edition}",
            )

        logger.warning(
            f"There is no bundle with hash {info.hash} in DB, "
            "but there is a dir on disk with this hash. Dir will be overwritten.",
        )

    untar_safe(to=info.root, tar_from=archive)

    try:
        inner_bundle_archive = _find_inner_archive(info.root)
    except FileNotFoundError as e:
        raise BundleParsingError("Bundle archive is empty") from e

    signature_file = _find_signature_file(info.root)
    if signature_file:
        if inner_bundle_archive:
            info.signature = _calculate_bundle_verification_status(
                bundle_archive=inner_bundle_archive, signature_file=signature_file, files_dir=files_dir, repo=repo
            )

        signature_file.unlink()

    if inner_bundle_archive:
        untar_safe(to=info.root, tar_from=inner_bundle_archive)
        inner_bundle_archive.unlink()

    return info


def _calculate_bundle_verification_status(
    bundle_archive: Path, signature_file: Path, files_dir: Path, repo: BundleRepoI
) -> SignatureStatus:
    # TAKEN FROM cm.bundle.get_verification_status
    # The keyring lives in a throwaway home: the default (~/.gnupg) is not
    # writable under a read-only rootfs, and importing the key needs a
    # writable keyring anyway.
    with TemporaryDirectory(prefix="bundle_verification_gpg_") as gpg_home:
        gpg = GPG(gpgbinary=os.popen("which gpg").read().strip(), gnupghome=gpg_home)  # noqa: S605, S607
        gpg.encoding = "utf-8"
        key_filepath = repo.retrieve_adcm_verification_public_key_path(files_dir)

        try:
            res = gpg.import_keys_file(key_path=key_filepath)
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
def cleanup(*, on_fail: Iterable[Path] = (), on_exit: Iterable[Path] = ()):
    try:
        yield
    except Exception:
        cleanup_by_remove_from_fs(on_fail)
        raise
    finally:
        cleanup_by_remove_from_fs(on_exit)


def cleanup_by_remove_from_fs(paths: Iterable[Path]) -> None:
    for path in paths:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            logger.warning(f"Path assigned for cleanup on error, but it's neither existing file or dir: {path}")


def verify_signature(bundle_signature: SignatureStatus, verified_signature_only: bool) -> None:
    if bundle_signature != SignatureStatus.VALID and verified_signature_only:
        raise BundleSignatureVerificationError(
            f"Upload rejected due to failed bundle verification: bundle's signature is '{bundle_signature.value}'"
        )


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

    raise BundleProcessingError("More than one tar file found")


def _find_signature_file(directory: Path) -> Path | None:
    signature_files = tuple(directory.glob("*.sig"))

    if not signature_files:
        return None

    if len(signature_files) == 1:
        return signature_files[0].absolute()

    raise BundleProcessingError('More than one ".sig" file found')


def _write_bundle_archive_to_tempdir(file_from_request: UploadedFileLike) -> Path:
    """Save file from request to tempdir, so it can be processed further"""
    tmp_path = Path(gettempdir(), str(file_from_request.name))

    with tmp_path.open(mode="wb+") as f:
        for chunk in file_from_request.chunks():
            f.write(chunk)

    return tmp_path


def _safe_copy_to_downloads(archive: Path, downloads_dir: Path) -> Path:
    """Copy file to downloads dir if there isn't already archive with such content"""
    target_path = downloads_dir / archive.name

    with _upload_fs_lock():
        existing_file = _find_duplicate(archive, in_=downloads_dir)
        if existing_file:
            message = f"Bundle already exists: Bundle with the same content is already uploaded {existing_file}"
            raise BundleProcessingError(message)

        # move to downloads
        shutil.move(src=archive, dst=target_path)

        return target_path

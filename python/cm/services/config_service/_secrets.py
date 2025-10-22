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

from typing import Callable, TypeVar
import json

from ansible.parsing.vault import VaultAES256, VaultSecret

T = TypeVar("T")


class AnsibleSecrets:
    def __init__(self) -> None:
        # Import it locally for laziness support.
        # There's no major need in django initialization for this init:
        # 1. Secret may be read independently
        # 2. Ansible secret header is constant, not an actual setting
        from django.conf import settings

        secret = settings.ANSIBLE_SECRET
        if not secret:
            if settings.SECRETS_FILE.is_file():
                # todo: temporal fallback to read secret from file,
                #       shouldn't be that way
                raw = settings.SECRETS_FILE.read_text()
                content = json.loads(raw)
                secret = content["adcmuser"]["password"]

            if not secret:
                message = "Ansible secret is undefined, work with secrets is impossible"
                raise ValueError(message)

        self._vault = VaultAES256()
        self._secret = VaultSecret(_bytes=str(secret).encode("utf-8"))
        self._encrypted_header = settings.ANSIBLE_VAULT_HEADER

    def is_encrypted(self, value: str) -> bool:
        return value.startswith(self._encrypted_header)

    def decrypt(self, value: str) -> str | None:
        """
        Decrypt string value if it's ansible encypted, otherwise return value itself.

        Avoid using this method directly, unless you know what you're doing:
        `reveal_secrets` is prefferred.
        """

        if not self.is_encrypted(value):
            return value

        _, ciphertext = value.split("\n", maxsplit=1)

        decrypted = self._vault.decrypt(b_vaulttext=ciphertext, secret=self._secret)

        if decrypted is None:
            # for some cases Ansible decryption may return `None` as a valid value
            return decrypted

        return decrypted.decode("utf-8")

    def encrypt(self, value: str) -> str:
        """
        Encrypt string value if it's not encrypted yet, otherwise return value itself
        """
        if self.is_encrypted(value):
            return value

        encrypted = self._vault.encrypt(b_plaintext=bytes(value, "utf-8"), secret=self._secret)
        return f"{self._encrypted_header}\n{encrypted.decode('utf-8')}"


def encrypt_if_possible(value: T, encryptor: Callable[[str], str]) -> T:
    if isinstance(value, str):
        return encryptor(value)

    if isinstance(value, dict):
        return {k: encrypt_if_possible(value=v, encryptor=encryptor) for k, v in value.items()}

    return value


def decrypt_if_possible(value: T, decryptor: Callable[[str], str | None]) -> T:
    if isinstance(value, str):
        return decryptor(value)

    if isinstance(value, dict):
        return {k: decrypt_if_possible(value=v, decryptor=decryptor) for k, v in value.items()}

    return value

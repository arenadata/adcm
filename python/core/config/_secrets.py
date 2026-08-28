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

from collections.abc import Callable
from typing import TypeVar

from ansible.parsing.vault import VaultAES256, VaultSecret

T = TypeVar("T")

ANSIBLE_VAULT_HEADER = "$ANSIBLE_VAULT;1.1;AES256"


class AnsibleSecrets:
    def __init__(self, secret: str) -> None:
        self._vault = VaultAES256()
        self._secret = VaultSecret(_bytes=str(secret).encode("utf-8"))
        self._encrypted_header = ANSIBLE_VAULT_HEADER

    def is_encrypted(self, value: str) -> bool:
        return value.startswith(self._encrypted_header)

    def decrypt(self, value: str) -> str:
        """
        Decrypt string value if it's ansible encypted, otherwise return value itself.
        """

        if not self.is_encrypted(value):
            return value

        _, ciphertext = value.split("\n", maxsplit=1)

        decrypted = self._vault.decrypt(b_vaulttext=ciphertext, secret=self._secret)

        if decrypted is None:
            # If I understood correctly, result of vault decrypt will be None only when both are true:
            # - PYCRYPTO is used instead of CRYPTOGRAPHY
            # - HMAC digest is not equal to expected one
            #
            # Since we use cryptography, it's not our case AND branch with PYCRYPTO returns UNKNOWN,
            # which most likely is `bytes`, yet it's not typed.
            #
            # Based on these two points, I decided to raise exception, because masking it is potentially dangerous.

            # value is expected to be decrypted, so it's safe to put it to message
            message = f"Decryption failed due to vault.decrypt returned `None` for {value}"
            raise RuntimeError(message)

        return decrypted.decode("utf-8")

    def encrypt(self, value: str) -> str:
        """
        Encrypt string value if it's not encrypted yet, otherwise return value itself
        Leave empty strings untouched (ADCM-8325)
        """
        if self.is_encrypted(value) or not value:
            return value

        encrypted = self._vault.encrypt(b_plaintext=bytes(value, "utf-8"), secret=self._secret)
        return f"{self._encrypted_header}\n{encrypted.decode('utf-8')}"


def encrypt_if_possible(value: T, encryptor: Callable[[str], str]) -> T:
    if isinstance(value, str):
        return encryptor(value)

    if isinstance(value, dict):
        # review within ADCM-7284
        return {k: encrypt_if_possible(value=v, encryptor=encryptor) for k, v in value.items()}  # pyright: ignore [reportReturnType]

    return value


def decrypt_if_possible(value: T, decryptor: Callable[[str], str | None]) -> T:
    if isinstance(value, str):
        return decryptor(value)

    if isinstance(value, dict):
        # review within ADCM-7284
        return {k: decrypt_if_possible(value=v, decryptor=decryptor) for k, v in value.items()}  # pyright: ignore [reportReturnType]

    return value

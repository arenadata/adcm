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

from ansible.parsing.vault import VaultAES256, VaultSecret


class AnsibleSecrets:
    def __init__(self) -> None:
        # Import it locally for laziness support.
        # There's no major need in django initialization for this init:
        # 1. Secret may be read independently
        # 2. Ansible secret header is constant, not an actual setting
        from django.conf import settings

        secret = settings.ANSIBLE_SECRET
        if not secret:
            message = "Ansible secret is undefined, work with secrets is impossible"
            raise ValueError(message)

        self._vault = VaultAES256()
        self._secret = VaultSecret(_bytes=str(secret).encode("utf-8"))
        self._encrypted_header = settings.ANSIBLE_VAULT_HEADER

    def reveal_secrets(self, source: dict) -> dict:
        """
        Recursively reveal ansible secrets from given source
        and return all values as new dictionary.

        Note: "nested" secrets are revealed only from `dict` and `list`,
        types like `tuple` and `deque` aren't currently supported.
        """

        result = {}

        for key, value in source.items():
            if isinstance(value, dict):
                result[key] = self.reveal_secrets(value)
            elif isinstance(value, list):
                result[key] = [entry if not isinstance(entry, dict) else self.reveal_secrets(entry) for entry in value]
            elif isinstance(value, str):
                result[key] = self.decrypt(value)
            else:
                result[key] = value

        return result

    def decrypt(self, value: str) -> str | None:
        """
        Decrypt string value if it's ansible encypted, otherwise return value itself.

        Avoid using this method directly, unless you know what you're doing:
        `reveal_secrets` is prefferred.
        """

        if self._encrypted_header not in value:
            return value

        _, ciphertext = value.split("\n", maxsplit=1)

        decrypted = self._vault.decrypt(b_vaulttext=ciphertext, secret=self._secret)

        if decrypted is None:
            # for some cases Ansible decryption may return `None` as a valid value
            return decrypted

        return decrypted.decode("utf-8")

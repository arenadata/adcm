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
from django.conf import settings


def ansible_encrypt(msg: str) -> bytes:
    vault = VaultAES256()
    secret = VaultSecret(_bytes=bytes(settings.ANSIBLE_SECRET, settings.ENCODING_UTF_8))

    return vault.encrypt(b_plaintext=bytes(msg, settings.ENCODING_UTF_8), secret=secret)


def ansible_encrypt_and_format(msg: str) -> str:
    ciphertext = ansible_encrypt(msg=msg)

    return f"{settings.ANSIBLE_VAULT_HEADER}\n{str(ciphertext, settings.ENCODING_UTF_8)}"


def ansible_decrypt(msg: str | None) -> str:
    if not isinstance(msg, str) or (settings.ANSIBLE_VAULT_HEADER not in msg and "__ansible_vault" not in msg):
        return msg or ""

    _, ciphertext = msg.split("\n")
    vault = VaultAES256()
    secret = VaultSecret(_bytes=bytes(settings.ANSIBLE_SECRET, settings.ENCODING_UTF_8))

    return str(vault.decrypt(b_vaulttext=ciphertext, secret=secret), settings.ENCODING_UTF_8)

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

from rest_framework.status import HTTP_200_OK
import yaml

from api_v2.tests.base import BaseAPITestCase

SCHEMA_PATH = Path(__file__).parent.parent.parent / "adcm" / "api_schema.yaml"


class TestAPISchema(BaseAPITestCase):
    def test_endpoints(self):
        response = self.client.v2["schema"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        api_schema = response.data

        content = SCHEMA_PATH.read_text(encoding="utf-8")
        documented_schema = yaml.safe_load(content)

        documented_schema, api_schema = self.clean_schema(documented_schema, api_schema)

        diffs = self.compare_schema_dicts(documented_schema, api_schema)

        self.assertFalse(
            diffs,
            "Schema differences:\n"
            + "\n".join(f"{' → '.join(path)}: {reason} ({values})" for path, reason, values in diffs),
        )

    def compare_schema_dicts(self, current_schema: dict, previous_schema: dict, path=()):
        """Recursively compare two schema dicts, return list of differences."""
        diffs = []

        if isinstance(current_schema, dict) and isinstance(previous_schema, dict):
            all_keys = set(current_schema) | set(previous_schema)
            for key in all_keys:
                new_path = path + (key,)
                if key not in current_schema:
                    diffs.append((new_path, "missing in previously existing", previous_schema[key]))
                elif key not in previous_schema:
                    diffs.append((new_path, "missing in current api", current_schema[key]))
                else:
                    diffs.extend(self.compare_schema_dicts(current_schema[key], previous_schema[key], new_path))
            return diffs

        if isinstance(current_schema, list) and isinstance(previous_schema, list):
            if len(current_schema) != len(previous_schema):
                diffs.append((path, "list length differs", (len(current_schema), len(previous_schema))))
            else:
                for i, (av, bv) in enumerate(zip(current_schema, previous_schema)):
                    diffs.extend(self.compare_schema_dicts(av, bv, path + (str(i),)))
            return diffs

        if current_schema != previous_schema:
            diffs.append((path, "value differs", (current_schema, previous_schema)))

        return diffs

    def clean_schema(self, documented_schema: dict, api_schema: dict) -> tuple[dict, dict]:
        """
        Normalize two OpenAPI schemas so UUIDs, timestamps, and volatile fields
        don't cause unnecessary diffs.
        """

        def scrub(obj):
            if isinstance(obj, dict):
                for k, v in list(obj.items()):
                    if k in ("version", "createdAt", "processSyncKey"):
                        obj[k] = "PLACEHOLDER"
                    else:
                        scrub(v)
            elif isinstance(obj, list):
                for i in obj:
                    scrub(i)
            return obj

        documented_schema = scrub(documented_schema)
        api_schema = scrub(api_schema)

        return documented_schema, api_schema

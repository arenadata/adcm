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
import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Subquery

from rbac.models import Role


def read_role(role: Role) -> dict:
    data = {
        "name": role.name,
        "type": role.type,
        "parametrized_by_type": role.parametrized_by_type,
        "category": [c.value for c in role.category.all()],
        "child": [read_role(r) for r in role.child.all()],
    }
    return data


class Command(BaseCommand):

    help = "Return role map to json file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--indent",
            type=int,
            default=2,
            help="Specifies the indent level to use when pretty-printing output.",
        )
        parser.add_argument(
            "-o",
            "--output",
            required=True,
            help="Specifies file to which the output is written.",
        )

    def handle(self, *args, **options):
        indent = options["indent"]
        output = options["output"]
        data = []

        # We should start from root of the forest, so we filter out
        # everything that is not mentioned as a child.
        for role in Role.objects.exclude(id__in=Subquery(Role.objects.filter(child__isnull=False).values("child__id"))):
            data.append(read_role(role))

        with open(output, "w", encoding=settings.ENCODING_UTF_8) as f:
            json.dump(data, f, indent=indent)
        self.stdout.write(self.style.SUCCESS(f"Result file: {output}"))

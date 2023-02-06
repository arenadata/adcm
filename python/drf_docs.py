#!/usr/bin/env python3
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

import adcm.init_django  # pylint: disable=unused-import
import api.urls


def fix_ordering(field, view):
    fix = field.replace("prototype__", "prototype_")
    fix = fix.replace("provider__", "provider_")
    fix = fix.replace("cluster__", "cluster_")
    fix = fix.replace("version_order", "version")
    if view.__name__ == "ClusterServiceList":
        if "display_name" in fix:
            fix = fix.replace("prototype_display_name", "display_name")
    elif view.__name__ == "ServiceComponentList":
        if "display_name" in fix:
            fix = fix.replace("component__display_name", "display_name")
    return fix


def drf_docs():
    for p in api.urls.urlpatterns:
        if not p.callback:
            continue
        if not hasattr(p.callback, "view_class"):
            continue

        order = filtr = None
        if hasattr(p.callback.view_class, "ordering_fields"):
            order = p.callback.view_class.ordering_fields
        if hasattr(p.callback.view_class, "filterset_fields"):
            filtr = p.callback.view_class.filterset_fields

        if not (order or filtr):
            continue

        print(f"{p.pattern}")
        if order:
            data = [fix_ordering(o, p.callback.view_class) for o in order]
            print(f"	ORDERING:  {data}")
        if filtr:
            data = [fix_ordering(f, p.callback.view_class) for f in filtr]
            print(f"	FILTERING: {data}")


drf_docs()

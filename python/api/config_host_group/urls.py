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


from rest_framework_extensions.routers import ExtendedSimpleRouter as SimpleRouter

from api.config_host_group.views import (
    CHGConfigLogViewSet,
    CHGConfigViewSet,
    CHGHostCandidateViewSet,
    CHGHostViewSet,
    CHGViewSet,
)

router = SimpleRouter()

root = router.register(r"", CHGViewSet, basename="group-config")
root.register(
    r"host",
    CHGHostViewSet,
    basename="group-config-host",
    parents_query_lookups=["config_host_group"],
)
root.register(
    r"host-candidate",
    CHGHostCandidateViewSet,
    basename="group-config-host-candidate",
    parents_query_lookups=["config_host_group"],
)
config = root.register(
    r"config",
    CHGConfigViewSet,
    basename="group-config-config",
    parents_query_lookups=["config_host_group"],
)
config.register(
    r"config-log",
    CHGConfigLogViewSet,
    basename="group-config-config-log",
    parents_query_lookups=["obj_ref__config_host_group", "obj_ref"],
)
urlpatterns = router.urls

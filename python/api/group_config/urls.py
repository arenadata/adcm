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


from rest_framework_extensions.routers import ExtendedDefaultRouter as DefaultRouter

from api.group_config.views import (
    GroupConfigConfigLogViewSet,
    GroupConfigConfigViewSet,
    GroupConfigHostCandidateViewSet,
    GroupConfigHostViewSet,
    GroupConfigViewSet,
)

router = DefaultRouter()

root = router.register(r"", GroupConfigViewSet, basename="group-config")
root.register(
    r"host",
    GroupConfigHostViewSet,
    basename="group-config-host",
    parents_query_lookups=["group_config"],
)
root.register(
    r"host-candidate",
    GroupConfigHostCandidateViewSet,
    basename="group-config-host-candidate",
    parents_query_lookups=["group_config"],
)
config = root.register(
    r"config",
    GroupConfigConfigViewSet,
    basename="group-config-config",
    parents_query_lookups=["group_config"],
)
config.register(
    r"config-log",
    GroupConfigConfigLogViewSet,
    basename="group-config-config-log",
    parents_query_lookups=["obj_ref__group_config", "obj_ref"],
)
urlpatterns = router.urls

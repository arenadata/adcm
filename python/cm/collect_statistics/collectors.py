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

from collections import defaultdict
from hashlib import md5
from typing import Collection, Literal

from core.types import BundleID, ClusterID
from django.db.models import Count, F, Q
from pydantic import BaseModel
from rbac.models import Policy, Role, User
from typing_extensions import TypedDict

from cm.models import Bundle, Cluster, HostComponent, HostInfo, Provider


class BundleData(TypedDict):
    name: str
    version: str
    edition: str
    date: str


class HostComponentData(TypedDict):
    host_name: str
    component_name: str
    service_name: str


class ClusterData(TypedDict):
    name: str
    host_count: int
    bundle: dict
    host_component_map: list[dict]
    hosts: list[dict]


class ProviderData(TypedDict):
    name: str
    host_count: int
    bundle: dict


class UserData(TypedDict):
    email: str
    date_joined: str


class RoleData(TypedDict):
    name: str
    built_in: bool


class ADCMEntities(BaseModel):
    clusters: list[ClusterData]
    bundles: list[BundleData]
    providers: list[ProviderData]


class RBACEntities(BaseModel):
    users: list[UserData]
    roles: list[RoleData]


class RBACCollector:
    def __init__(self, date_format: str):
        self._date_format = date_format

    def __call__(self) -> RBACEntities:
        return RBACEntities(
            users=[
                UserData(email=email, date_joined=date_joined.strftime(self._date_format))
                for email, date_joined in User.objects.values_list("email", "date_joined")
            ],
            roles=[
                RoleData(**role)
                for role in Role.objects.filter(
                    pk__in=Policy.objects.filter(role__isnull=False).values_list("role_id", flat=True).distinct()
                ).values("name", "built_in")
            ],
        )


def get_host_name_hash(name: str) -> str:
    return md5(name.encode(encoding="utf-8")).hexdigest()  # noqa: S324


class BundleCollector:
    __slots__ = ("_date_format", "_filters", "_postprocess_result")

    def __init__(self, date_format: str, filters: Collection[Q] = ()):
        self._date_format = date_format
        self._filters = filters

    def __call__(self) -> ADCMEntities:
        bundles: dict[BundleID, BundleData] = {
            entry.pop("id"): BundleData(date=entry.pop("date").strftime(self._date_format), **entry)
            for entry in Bundle.objects.filter(*self._filters).values("id", *BundleData.__annotations__.keys())
        }

        providers_data = [
            ProviderData(name=entry["name"], host_count=entry["host_count"], bundle=bundles[entry["bundle_id"]])
            for entry in Provider.objects.filter(prototype__bundle_id__in=bundles.keys())
            .values("name", bundle_id=F("prototype__bundle_id"))
            .annotate(host_count=Count("host"))
        ]

        cluster_general_info: dict[ClusterID, dict[Literal["name", "bundle_id", "host_count"], int | str]] = {
            entry.pop("id"): entry
            for entry in Cluster.objects.filter(prototype__bundle_id__in=bundles.keys())
            .values("id", "name", bundle_id=F("prototype__bundle_id"))
            .annotate(host_count=Count("host"))
        }

        hostcomponent_data = defaultdict(list)
        for entry in HostComponent.objects.filter(cluster_id__in=cluster_general_info.keys()).values(
            "cluster_id",
            host_name=F("host__fqdn"),
            component_name=F("component__prototype__name"),
            service_name=F("service__prototype__name"),
        ):
            hostcomponent_data[entry.pop("cluster_id")].append(
                HostComponentData(
                    host_name=get_host_name_hash(entry.pop("host_name")),
                    **entry,
                )
            )

        host_data = defaultdict(list)
        for host_name, host_cluster_id, host_facts in HostInfo.objects.values_list(
            "host__fqdn", "host__cluster_id", "value"
        ).filter(host__cluster_id__in=cluster_general_info.keys()):
            related_bundle_edition = bundles[cluster_general_info[host_cluster_id]["bundle_id"]]["edition"]
            if related_bundle_edition != "enterprise":
                # we gather only family if edition isn't enterprise and
                host_facts["os"] = {"family": family} if (family := host_facts["os"].get("family")) else {}

            host_data[host_cluster_id].append({"name": get_host_name_hash(host_name), "info": host_facts})

        clusters_data = [
            ClusterData(
                name=data["name"],
                host_count=data["host_count"],
                bundle=bundles[data["bundle_id"]],
                host_component_map=hostcomponent_data.get(cluster_id, []),
                hosts=host_data.get(cluster_id, []),
            )
            for cluster_id, data in cluster_general_info.items()
        ]

        return ADCMEntities(clusters=clusters_data, bundles=bundles.values(), providers=providers_data)

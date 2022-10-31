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

from typing import Optional, Set, Tuple

from cm.models import (
    ADCMEntity,
    ClusterObject,
    Host,
    HostComponent,
    MaintenanceMode,
    ServiceComponent,
)


class HierarchyError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.msg = kwargs.get('msg') or args[0] if args else 'Hierarchy build error'


class Node:
    """
    Node of hierarchy tree
    Each node has zero to many parents and zero to many children
    """

    order = ('root', 'cluster', 'service', 'component', 'host', 'provider')

    def __init__(self, value: Optional[ADCMEntity]):
        self.children = set()
        if value is None:  # tree virtual root
            self.id = 0
            self.type = 'root'
            self.value = None
            self.parents = tuple()
        else:
            if not hasattr(value, 'prototype'):
                raise HierarchyError(f'Type <{type(value)}> is not part of hierarchy')
            self.id = value.pk
            self.type = value.prototype.type
            self.value = value
            self.parents = set()

    def add_child(self, child: 'Node') -> None:
        if child in self.parents or child == self:
            raise HierarchyError("Hierarchy should not have cycles")
        self.children.add(child)

    def add_parent(self, parent: 'Node') -> None:
        if parent in self.children or parent == self:
            raise HierarchyError("Hierarchy should not have cycles")
        self.parents.add(parent)

    def get_parents(self) -> Set['Node']:
        """Get own parents and all its ancestors"""
        result = set(self.parents)
        for parent in self.parents:
            result.update(parent.get_parents())
        return result

    def get_children(self) -> Set['Node']:
        """Get own children and all its descendants"""
        result = set(self.children)
        for child in self.children:
            result.update(child.get_children())
        return result

    @staticmethod
    def get_obj_key(obj: ADCMEntity) -> Tuple[str, int]:
        """Make simple unique key for caching in tree"""
        if obj is None:
            return 'root', 0
        return obj.prototype.type, obj.pk

    @property
    def key(self) -> Tuple[str, int]:
        """Simple key unique in tree"""
        return self.type, self.id

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return self.key == other.key


class Tree:
    """
    Hierarchy tree class keep links and relations between its nodes like this:
        common_virtual_root -> *cluster -> *service -> *component -> *host -> provider
    """

    def __init__(self, obj: ADCMEntity):
        self.root = Node(value=None)
        self._nodes = {self.root.key: self.root}
        self.built_from = self._make_node(obj)
        self._build_tree_up(self.built_from)  # go to the root ...
        self._build_tree_down(self.root)  # ... and find all its children

    def _make_node(self, obj: ADCMEntity) -> Node:
        cached = self._nodes.get(Node.get_obj_key(obj))
        if cached:
            return cached
        else:
            node = Node(value=obj)
            self._nodes[node.key] = node
            return node

    def _build_tree_down(self, node: Node) -> None:
        if node.type == 'root':
            children_values = [n.value for n in node.children]

        if node.type == 'cluster':
            children_values = ClusterObject.objects.filter(cluster=node.value).all()

        elif node.type == 'service':
            children_values = ServiceComponent.objects.filter(
                cluster=node.value.cluster, service=node.value
            ).all()

        elif node.type == 'component':
            children_values = [
                c.host
                for c in HostComponent.objects.filter(
                    cluster=node.value.service.cluster,
                    service=node.value.service,
                    component=node.value,
                )
                .select_related('host')
                .all()
            ]

        elif node.type == 'host':
            children_values = []

        elif node.type == 'provider':
            children_values = Host.objects.filter(provider=node.value)

        for value in children_values:
            child = self._make_node(value)
            node.add_child(child)
            child.add_parent(node)
            self._build_tree_down(child)

    def _build_tree_up(self, node: Node) -> None:
        parent_values = []
        if node.type == 'cluster':
            parent_values = [None]
        elif node.type == 'service':
            parent_values = [node.value.cluster]
        elif node.type == 'component':
            parent_values = [node.value.service]
        elif node.type == 'host':
            parent_values = [
                hc.component
                for hc in HostComponent.objects.filter(host=node.value)
                .exclude(host__maintenance_mode=MaintenanceMode.ON)
                .select_related('component')
                .all()
            ]
        elif node.type == 'provider':
            parent_values = Host.objects.filter(provider=node.value).all()

        for value in parent_values:
            parent = self._make_node(value)
            node.add_parent(parent)
            parent.add_child(node)
            self._build_tree_up(parent)

    def get_node(self, obj: ADCMEntity) -> Node:
        """Get tree node by its object"""
        key = Node.get_obj_key(obj)
        cached = self._nodes.get(key)
        if cached:
            return cached
        else:
            raise HierarchyError(f'Object {key} is not part of tree')

    def get_directly_affected(self, node: Node) -> Set[Node]:
        """Collect directly affected nodes for issues re-calc"""
        result = {node}
        result.update(node.get_parents())
        result.update(node.get_children())
        result.discard(self.root)
        return result

    def get_all_affected(self, node: Node) -> Set[Node]:
        """Collect directly affected nodes and propagate effect back through affected hosts"""
        directly_affected = self.get_directly_affected(node)
        indirectly_affected = set()
        for host_node in filter(lambda x: x.type == 'host', directly_affected):
            indirectly_affected.update(host_node.get_parents())
        result = indirectly_affected.union(directly_affected)
        result.discard(self.root)
        return result

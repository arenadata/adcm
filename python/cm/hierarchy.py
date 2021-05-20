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

from itertools import chain
from typing import Set, Optional, Tuple

from cm.models import (
    ADCM,
    ADCMModel,
    HierarchyMember,
    Cluster,
    ClusterObject,
    HostProvider,
    Host,
    HostComponent,
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

    def __init__(self, value: Optional[ADCMModel]):
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
    def get_obj_key(obj) -> Tuple[str, int]:
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

    def __init__(self, obj):
        self.root = Node(value=None)
        self._nodes = {self.root.key: self.root}
        self.built_from = self._make_node(obj)
        self._build_tree_up(self.built_from)  # go to the root ...
        self._build_tree_down(self.root)  # ... and find all its children

    def _make_node(self, obj) -> Node:
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
            children_values = ClusterObject.objects.filter(cluster=node.value)

        elif node.type == 'service':
            children_values = ServiceComponent.objects.filter(
                cluster=node.value.cluster,
                service=node.value
            )

        elif node.type == 'component':
            children_values = [
                c.host for c in HostComponent.objects.filter(
                    cluster=node.value.service.cluster,
                    service=node.value.service,
                    component=node.value
                )
            ]

        elif node.type == 'host':
            children_values = [node.value.provider]

        elif node.type == 'provider':
            children_values = []

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
            parent_values = [hc.component for hc in HostComponent.objects.filter(host=node.value)]
        elif node.type == 'provider':
            parent_values = Host.objects.filter(provider=node.value)

        for value in parent_values:
            parent = self._make_node(value)
            node.add_parent(parent)
            parent.add_child(node)
            self._build_tree_up(parent)

    def get_node(self, obj) -> Node:
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


# ------------------- POC changes to classes above ------------------------


class ANode:
    """
    Node of hierarchy tree
    Each node has zero to many parents and zero to many children
    """
    def __init__(self, value: HierarchyMember):
        self.id = value.pk
        self.type = value.prototype.type
        self.value = value
        self.parents = set()
        self.children = set()

    def add_child(self, child: 'ANode') -> None:
        if child in self.parents or child == self:
            return
        self.children.add(child)

    def add_parent(self, parent: 'ANode') -> None:
        if parent in self.children or parent == self:
            return
        self.parents.add(parent)

    def get_parents(self) -> Set['ANode']:
        """Get own parents and all its ancestors"""
        result = set(self.parents)
        for parent in self.parents:
            result.update(parent.get_parents())
        return result

    def get_children(self) -> Set['ANode']:
        """Get own children and all its descendants"""
        result = set(self.children)
        for child in self.children:
            result.update(child.get_children())
        return result

    @staticmethod
    def get_obj_key(obj: HierarchyMember) -> Tuple[str, int]:
        """Make simple unique key for caching in tree"""
        return obj.prototype.type, obj.pk

    @property
    def key(self) -> Tuple[str, int]:
        """Simple key unique in tree"""
        return self.type, self.id

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return self.key == other.key


class ATree:
    """
    Hierarchy tree class keep links and relations between its nodes like this:
        common_virtual_root -> *cluster -> *service -> *component -> *host -> provider
    """

    def __init__(self, obj: HierarchyMember):
        self._nodes = {}
        self.root = self._make_node(ADCM.objects.get(name='ADCM'))
        self.built_from = self._make_node(obj)
        self._build_tree(obj)
        # self._build_tree(self.built_from)  # go to the root ...
        # self._build_tree_down(self.root)  # ... and find all its children

    def _make_node(self, obj: HierarchyMember) -> ANode:
        cached = self._nodes.get(ANode.get_obj_key(obj))
        if cached:
            return cached
        else:
            node = ANode(value=obj)
            self._nodes[node.key] = node
            return node

    # def _find_subroots(self, obj: HierarchyMember) -> None:
    #     nodes = set()
    #
    #     cluster = getattr(obj, 'cluster', None)
    #     if cluster:
    #         nodes.add(self._make_node(cluster))
    #
    #     provider = getattr(obj, 'provider', None)
    #     if provider:
    #         nodes.add(self._make_node(provider))

    # def _build_tree_down(self, node: ANode) -> None:
    #     if node.type == 'adcm':
    #         children_values = [n.value for n in node.children]  # do not collect all clusters
    #     else:
    #         children_values = node.value.get_children()
    #
    #     # add provider-host branches to the tree without recursion
    #     if node.type == 'host':
    #         for provider in node.value.get_parents():
    #             provider_node = self._make_node(provider)
    #             provider_node.add_parent(self.root)
    #             provider_node.add_child(node)
    #
    #     for value in children_values:
    #         child = self._make_node(value)
    #         node.add_child(child)
    #         child.add_parent(node)
    #         self._build_tree_down(child)

    # def _build_tree_up(self, node: ANode) -> None:
    #     for obj in node.value.get_parents():
    #         parent = self._make_node(obj)
    #         node.add_parent(parent)
    #         parent.add_child(node)
    #         self._build_tree_up(parent)

    def _build_tree(self, obj: HierarchyMember) -> None:
        if obj.prototype.type == 'adcm':
            return  # TODO: do something when needed
        elif obj.prototype.type == 'provider':
            self._build_subtree(obj)
            for host in [n.value for n in self._nodes.values() if n.type == 'host']:
                self._build_subtree(host.cluster)
        else:
            cluster = obj if obj.prototype.type == 'cluster' else getattr(obj, 'cluster', None)
            self._build_subtree(cluster)
            for host in [n.value for n in self._nodes.values() if n.type == 'host']:
                self._build_subtree(host.provider)

    def _build_subtree(self, obj: Optional[HierarchyMember]) -> None:
        if not obj:
            return

        node = self._make_node(obj)
        for child in obj.get_children():
            child_node = self._make_node(child)
            node.add_child(child_node)
            child_node.add_parent(node)
            self._build_subtree(child)

    def get_node(self, obj: HierarchyMember) -> ANode:
        """Get tree node by its object"""
        key = ANode.get_obj_key(obj)
        cached = self._nodes.get(key)
        if cached:
            return cached
        else:
            raise HierarchyError(f'Object {key} is not part of tree')

    def get_directly_affected(self, node: ANode) -> Set[ANode]:
        """Collect directly affected nodes for issues re-calc"""
        result = {node}
        result.update(node.get_parents())
        result.update(node.get_children())
        result.discard(self.root)
        return result

    def get_all_affected(self, node: ANode) -> Set[ANode]:
        """Collect directly affected nodes and propagate effect back through affected hosts"""
        directly_affected = self.get_directly_affected(node)
        indirectly_affected = set()
        for host_node in filter(lambda x: x.type == 'host', directly_affected):
            indirectly_affected.update(host_node.get_parents())
        result = indirectly_affected.union(directly_affected)
        result.discard(self.root)
        return result

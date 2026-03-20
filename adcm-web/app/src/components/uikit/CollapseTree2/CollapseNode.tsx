import type { ReactNode, RefObject } from 'react';
import { useEffect, useState, useCallback } from 'react';
import Collapse from '@uikit/Collapse/Collapse';
import type { Node } from './CollapseNode.types';
import s from './CollapseNode.module.scss';
import cn from 'classnames';
import type { ConfigurationNode } from '@uikit/ConfigurationEditor/ConfigurationEditor.types';
import {
  rootNodeKey,
  toggleAllNodesEventName,
} from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree.constants';

interface CollapseNodeProps<T> {
  node: Node<T>;
  treeRef?: RefObject<HTMLDivElement>;
  isInitiallyExpanded?: boolean;
  areExpandedAll?: boolean;
  getNodeClassName: (node: Node<T>) => string;
  renderNodeContent: (node: Node<T>, isExpanded: boolean, onExpand: (isOpen: boolean) => void) => ReactNode;
}

const CollapseNode = <T,>({
  node,
  treeRef,
  isInitiallyExpanded = false,
  areExpandedAll,
  getNodeClassName,
  renderNodeContent,
}: CollapseNodeProps<T>) => {
  const isIgnoreExpandAll = node.key === rootNodeKey;
  const initialExpanded = areExpandedAll !== undefined && !isIgnoreExpandAll ? areExpandedAll : isInitiallyExpanded;
  const [isExpanded, setIsExpanded] = useState(initialExpanded);
  const hasChildren = Boolean(node.children?.length);
  const children = (node.children ?? []) as Node<T>[];
  const fieldAttributes = (node as ConfigurationNode).data.fieldAttributes;
  const isNodeCanBeExpanded = fieldAttributes?.isActive !== false;
  const isNodeExpanded = isNodeCanBeExpanded && isExpanded;

  const handleToggleAllNodes = useCallback(
    (e: CustomEvent<boolean>) => {
      if (!isIgnoreExpandAll) {
        setIsExpanded(e.detail);
      }
    },
    [isIgnoreExpandAll],
  );

  useEffect(() => {
    const localTreeRef = treeRef?.current;
    localTreeRef?.addEventListener(toggleAllNodesEventName, handleToggleAllNodes as EventListener);

    return () => {
      localTreeRef?.removeEventListener(toggleAllNodesEventName, handleToggleAllNodes as EventListener);
    };
  }, [treeRef, handleToggleAllNodes]);

  const toggleCollapseNode = (isOpen: boolean) => {
    if (hasChildren) {
      setIsExpanded(isOpen);
    }
  };

  return (
    <div className={cn(s.collapseNode, getNodeClassName(node), 'collapseNode')} data-test="node-container">
      <div className={cn(s.collapseNode__trigger, 'collapseNode__trigger')} data-test="node-block">
        {renderNodeContent(node, isNodeExpanded, toggleCollapseNode)}
      </div>
      {hasChildren && (
        <div className={cn(s.collapseNode__children, 'collapseNode__children')} data-test="children-block">
          <Collapse isExpanded={isNodeExpanded}>
            {children.map((childNode) => (
              <CollapseNode
                node={childNode}
                treeRef={treeRef}
                key={childNode.key}
                areExpandedAll={areExpandedAll}
                getNodeClassName={getNodeClassName}
                renderNodeContent={renderNodeContent}
              />
            ))}
          </Collapse>
        </div>
      )}
    </div>
  );
};

export default CollapseNode;

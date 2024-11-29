import type { ReactNode } from 'react';
import React, { useEffect, useState, useMemo, useCallback } from 'react';
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
  treeRef?: React.RefObject<HTMLDivElement>;
  isInitiallyExpanded?: boolean;
  getNodeClassName: (node: Node<T>) => string;
  renderNodeContent: (node: Node<T>, isExpanded: boolean, onExpand: (isOpen: boolean) => void) => ReactNode;
}

const CollapseNode = <T,>({
  node,
  treeRef,
  isInitiallyExpanded = false,
  getNodeClassName,
  renderNodeContent,
}: CollapseNodeProps<T>) => {
  const [isExpanded, setIsExpanded] = useState(isInitiallyExpanded);
  const hasChildren = Boolean(node.children?.length);
  const children = (node.children ?? []) as Node<T>[];
  const fieldAttributes = (node as ConfigurationNode).data.fieldAttributes;
  const isNodeExpanded = useMemo(
    () => (fieldAttributes?.isActive && isExpanded) ?? isExpanded,
    [fieldAttributes, isExpanded],
  );

  const isIgnoreExpandAll = useMemo(() => {
    return fieldAttributes?.isActive === false || node.key === rootNodeKey;
  }, [fieldAttributes, node]);

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
    <div className={cn(s.collapseNode, getNodeClassName(node))} data-test="node-container">
      <div className={s.collapseNode__trigger} data-test="node-block">
        {renderNodeContent(node, isExpanded, toggleCollapseNode)}
      </div>
      {hasChildren && (
        <div className={s.collapseNode__children} data-test="children-block">
          <Collapse isExpanded={isNodeExpanded}>
            {children.map((childNode) => (
              <CollapseNode
                node={childNode}
                treeRef={treeRef}
                key={childNode.key}
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

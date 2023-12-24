import React, { ReactNode, useEffect, useState, useMemo } from 'react';
import Collapse from '@uikit/Collapse/Collapse';
import { Node } from './CollapseNode.types';
import s from './CollapseNode.module.scss';
import cn from 'classnames';
import { ConfigurationNode } from '@uikit/ConfigurationEditor/ConfigurationEditor.types';
import { rootNodeKey } from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree.constants';

interface CollapseNodeProps<T> {
  node: Node<T>;
  isInitiallyExpanded?: boolean;
  areExpandedAll?: boolean;
  getNodeClassName: (node: Node<T>) => string;
  renderNodeContent: (node: Node<T>, isExpanded: boolean, onExpand: (isOpen: boolean) => void) => ReactNode;
}

const CollapseNode = <T,>({
  node,
  isInitiallyExpanded = false,
  areExpandedAll,
  getNodeClassName,
  renderNodeContent,
}: CollapseNodeProps<T>) => {
  const [isExpanded, setIsExpanded] = useState(isInitiallyExpanded);
  const hasChildren = Boolean(node.children?.length);
  const children = (node.children ?? []) as Node<T>[];

  const isIgnoreExpandAll = useMemo(() => {
    const fieldAttributes = (node as ConfigurationNode).data.fieldAttributes;

    return fieldAttributes?.isActive === false || node.key === rootNodeKey;
  }, [node]);

  useEffect(() => {
    if (!isIgnoreExpandAll && typeof areExpandedAll === 'boolean') {
      setIsExpanded(areExpandedAll);
    }
  }, [areExpandedAll, isIgnoreExpandAll]);

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
          <Collapse isExpanded={isExpanded}>
            {children.map((childNode) => (
              <CollapseNode
                node={childNode}
                key={childNode.key}
                getNodeClassName={getNodeClassName}
                renderNodeContent={renderNodeContent}
                areExpandedAll={areExpandedAll}
              />
            ))}
          </Collapse>
        </div>
      )}
    </div>
  );
};

export default CollapseNode;

import React, { ReactNode, useState } from 'react';
import Collapse from '@uikit/Collapse/Collapse';
import { Node } from './CollapseNode.types';
import s from './CollapseNode.module.scss';
import cn from 'classnames';

interface CollapseNodeProps<T> {
  node: Node<T>;
  getNodeClassName: (node: Node<T>) => string;
  renderNodeContent: (node: Node<T>, isExpanded: boolean, onExpand: (isOpen: boolean) => void) => ReactNode;
}

const CollapseNode = <T,>({ node, getNodeClassName, renderNodeContent }: CollapseNodeProps<T>) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = Boolean(node.children?.length);
  const children = (node.children ?? []) as Node<T>[];

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
              />
            ))}
          </Collapse>
        </div>
      )}
    </div>
  );
};

export default CollapseNode;

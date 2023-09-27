import React from 'react';
import cn from 'classnames';
import { Icon } from '@uikit';
import s from './NodeContent.module.scss';

export type Node = { title: string; children?: Node[]; isValid: boolean };

interface CollapseTreeNodeProps {
  node: Node;
  isExpanded: boolean;
  isSelected: boolean;
  onClick: (node: Node) => void;
}

const NodeContent: React.FC<CollapseTreeNodeProps> = ({ node, isExpanded, isSelected, onClick }) => {
  const className = cn(s.nodeContent, {
    'is-open': isExpanded,
    'is-selected': isSelected,
    'is-failed': !node.isValid,
  });

  const handleClick = () => {
    onClick(node);
  };

  return (
    <div className={className} onClick={handleClick}>
      {!node.isValid && <Icon size={14} name="alert-circle" />}
      <span className={s.nodeContent__title}>{node.title}</span>
      {node.children?.length && <Icon name="chevron" size={12} className={s.nodeContent__arrow} />}
    </div>
  );
};

export default NodeContent;

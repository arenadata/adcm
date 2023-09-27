import { useRef } from 'react';
import { Icon } from '@uikit';
import { Node } from '@uikit/CollapseTree2/CollapseNode.types';
import { ConfigurationField, ConfigurationNode } from '../../ConfigurationEditor.types';
import s from '../ConfigurationTree.module.scss';
import cn from 'classnames';

interface FieldNodeContentProps {
  node: ConfigurationNode;
  hasError: boolean;
  onClick: (node: ConfigurationNode, nodeRef: React.RefObject<HTMLElement>) => void;
  onDeleteClick: (node: ConfigurationNode, nodeRef: React.RefObject<HTMLElement>) => void;
}

const FieldNodeContent = ({ node, hasError, onClick, onDeleteClick }: FieldNodeContentProps) => {
  const ref = useRef(null);
  const fieldNode = node as Node<ConfigurationField>;
  const adcmMeta = fieldNode.data.fieldSchema.adcmMeta;

  const handleClick = () => {
    if (!fieldNode.data.isReadonly) {
      onClick(node, ref);
    }
  };

  const handleDeleteClick = () => {
    onDeleteClick(node, ref);
  };

  const className = cn(s.nodeContent, {
    // 'is-selected': isSelected,
    'is-failed': hasError,
  });

  const value = fieldNode.data.value ?? 'NULL';

  return (
    <div ref={ref} className={className}>
      {fieldNode.data.isDeletable && <Icon size={16} name="g1-delete" onClick={handleDeleteClick} />}
      {hasError && <Icon size={14} name="alert-circle" />}
      <span className={s.nodeContent__title}>{fieldNode.data.title}: </span>
      <span className={s.nodeContent__value} onClick={handleClick}>
        {adcmMeta.isSecret ? '***' : value.toString()}
      </span>
    </div>
  );
};

export default FieldNodeContent;

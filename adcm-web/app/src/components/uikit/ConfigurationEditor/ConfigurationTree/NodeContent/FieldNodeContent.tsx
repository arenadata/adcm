import { useCallback, useRef } from 'react';
import { Icon } from '@uikit';
import { Node } from '@uikit/CollapseTree2/CollapseNode.types';
import { ConfigurationField, ConfigurationNode } from '../../ConfigurationEditor.types';
import s from '../ConfigurationTree.module.scss';
import cn from 'classnames';
import ActivationAttribute from './ActivationAttribute/ActivationAttribute';
import SynchronizedAttribute from './SyncronizedAttribute/SynchronizedAttribute';
import { ChangeFieldAttributesHandler } from '../ConfigurationTree.types';

interface FieldNodeContentProps {
  node: ConfigurationNode;
  hasError: boolean;
  onClick: (node: ConfigurationNode, nodeRef: React.RefObject<HTMLElement>) => void;
  onDeleteClick: (node: ConfigurationNode, nodeRef: React.RefObject<HTMLElement>) => void;
  onFieldAttributeChange: ChangeFieldAttributesHandler;
}

const FieldNodeContent = ({
  node,
  hasError,
  onClick,
  onDeleteClick,
  onFieldAttributeChange,
}: FieldNodeContentProps) => {
  const ref = useRef(null);
  const fieldNode = node as Node<ConfigurationField>;
  const adcmMeta = fieldNode.data.fieldSchema.adcmMeta;
  const fieldAttributes = node.data.fieldAttributes;

  const handleIsActiveChange = useCallback(
    (isActive: boolean) => {
      if (fieldAttributes) {
        onFieldAttributeChange(node.key, { ...fieldAttributes, isActive });
      }
    },
    [fieldAttributes, node.key, onFieldAttributeChange],
  );

  const handleIsSynchronizedChange = useCallback(
    (isSynchronized: boolean) => {
      if (fieldAttributes) {
        onFieldAttributeChange(node.key, { ...fieldAttributes, isSynchronized });
      }
    },
    [fieldAttributes, node.key, onFieldAttributeChange],
  );

  const handleClick = () => {
    onClick(node, ref);
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
      {adcmMeta.activation && fieldAttributes && (
        <ActivationAttribute
          isActive={fieldAttributes.isActive}
          {...adcmMeta.activation}
          onToggle={handleIsActiveChange}
        />
      )}
      {fieldNode.data.isDeletable && <Icon size={16} name="g1-delete" onClick={handleDeleteClick} />}
      {hasError && <Icon size={14} name="alert-circle" />}
      <span className={s.nodeContent__title}>{fieldNode.data.title}: </span>
      {adcmMeta.synchronization && fieldAttributes && (
        <SynchronizedAttribute
          isSynchronized={fieldAttributes.isSynchronized}
          {...adcmMeta.synchronization}
          onToggle={handleIsSynchronizedChange}
        />
      )}
      <span className={s.nodeContent__value} onClick={handleClick}>
        {adcmMeta.isSecret ? '***' : value.toString()}
      </span>
    </div>
  );
};

export default FieldNodeContent;

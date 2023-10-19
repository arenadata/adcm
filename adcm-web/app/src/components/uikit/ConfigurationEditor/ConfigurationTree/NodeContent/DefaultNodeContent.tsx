import { useCallback, useRef } from 'react';
import { Icon } from '@uikit';

import { ConfigurationNode } from '../../ConfigurationEditor.types';
import { ChangeFieldAttributesHandler } from '../ConfigurationTree.types';
import s from '../ConfigurationTree.module.scss';
import cn from 'classnames';
import SynchronizedAttribute from './SyncronizedAttribute/SynchronizedAttribute';
import ActivationAttribute from './ActivationAttribute/ActivationAttribute';

interface DefaultNodeContentProps {
  node: ConfigurationNode;
  error?: string;
  isExpanded: boolean;
  onDelete: (node: ConfigurationNode, nodeRef: React.RefObject<HTMLElement>) => void;
  onExpand: () => void;
  onFieldAttributeChange: ChangeFieldAttributesHandler;
}

const DefaultNodeContent = ({
  node,
  isExpanded,
  error,
  onDelete,
  onExpand,
  onFieldAttributeChange,
}: DefaultNodeContentProps) => {
  const ref = useRef(null);
  const adcmMeta = node.data.fieldSchema.adcmMeta;
  const fieldAttributes = node.data.fieldAttributes;
  const isDeletable = node.data.type === 'object' && node.data.isDeletable;

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

  const handleDeleteClick = () => {
    onDelete(node, ref);
  };

  const className = cn(s.nodeContent, {
    'is-open': isExpanded,
    'is-failed': error !== undefined,
  });

  const hasChildren = Boolean(node.children?.length);

  return (
    <div className={className} ref={ref}>
      {adcmMeta.activation && fieldAttributes && (
        <ActivationAttribute
          isActive={fieldAttributes.isActive}
          {...adcmMeta.activation}
          onToggle={handleIsActiveChange}
        />
      )}

      {isDeletable && <Icon size={16} name="g1-delete" onClick={handleDeleteClick} />}
      <span className={s.nodeContent__title}>{node.data.title}</span>
      {adcmMeta.synchronization && fieldAttributes && (
        <SynchronizedAttribute
          isSynchronized={fieldAttributes.isSynchronized}
          {...adcmMeta.synchronization}
          onToggle={handleIsSynchronizedChange}
        />
      )}
      {hasChildren && <Icon name="chevron" size={12} className={s.nodeContent__arrow} onClick={onExpand} />}
    </div>
  );
};

export default DefaultNodeContent;

import { useCallback, useRef } from 'react';
import { IconButton } from '@uikit';

import { ConfigurationArray, ConfigurationObject, ConfigurationNode } from '../../ConfigurationEditor.types';
import { ChangeConfigurationNodeHandler, ChangeFieldAttributesHandler } from '../ConfigurationTree.types';
import s from '../ConfigurationTree.module.scss';
import cn from 'classnames';
import SynchronizedAttribute from './SyncronizedAttribute/SynchronizedAttribute';
import ActivationAttribute from './ActivationAttribute/ActivationAttribute';
import { nullStub } from '../ConfigurationTree.constants';

interface NodeWithChildrenContentProps {
  node: ConfigurationNode;
  error?: string;
  isExpanded: boolean;
  onClear: ChangeConfigurationNodeHandler;
  onDelete: ChangeConfigurationNodeHandler;
  onExpand: (isOpen: boolean) => void;
  onFieldAttributeChange: ChangeFieldAttributesHandler;
}

const NodeWithChildrenContent = ({
  node,
  isExpanded,
  error,
  onClear,
  onDelete,
  onExpand,
  onFieldAttributeChange,
}: NodeWithChildrenContentProps) => {
  const ref = useRef(null);
  const fieldNodeData = node.data as ConfigurationObject | ConfigurationArray;
  const adcmMeta = node.data.fieldSchema.adcmMeta;
  const fieldAttributes = node.data.fieldAttributes;
  // const isDeletable = node.data.type === 'object' && node.data.isDeletable;
  const isDeletable = (node.data.type === 'object' || node.data.type === 'array') && node.data.isDeletable;

  const handleIsActiveChange = useCallback(
    (isActive: boolean) => {
      if (fieldAttributes) {
        onFieldAttributeChange(node.key, { ...fieldAttributes, isActive });
      }

      onExpand(isActive);
    },
    [fieldAttributes, node.key, onFieldAttributeChange, onExpand],
  );

  const handleIsSynchronizedChange = useCallback(
    (isSynchronized: boolean) => {
      if (fieldAttributes) {
        onFieldAttributeChange(node.key, { ...fieldAttributes, isSynchronized });
      }
    },
    [fieldAttributes, node.key, onFieldAttributeChange],
  );

  const handleClearClick = () => {
    onClear(node, ref);
  };

  const handleDeleteClick = () => {
    onDelete(node, ref);
  };

  const handleExpandClick = () => {
    onExpand(!isExpanded);
  };

  const className = cn(s.nodeContent, {
    'is-open': isExpanded,
    'is-failed': error !== undefined,
  });

  const hasChildren = Boolean(node.children?.length);
  const isExpandable = fieldAttributes?.isActive === undefined ? hasChildren : Boolean(fieldAttributes.isActive);

  return (
    <div className={className} ref={ref}>
      {adcmMeta.activation && fieldAttributes && (
        <ActivationAttribute
          isActive={fieldAttributes.isActive}
          {...adcmMeta.activation}
          onToggle={handleIsActiveChange}
        />
      )}

      {fieldNodeData.isCleanable && fieldNodeData.value !== null && (
        <IconButton size={14} icon="g3-clear" onClick={handleClearClick} data-test="clear-btn" />
      )}
      {isDeletable && <IconButton size={14} icon="g3-delete" onClick={handleDeleteClick} data-test="delete-btn" />}
      <span className={s.nodeContent__title} data-test="node-name">
        {node.data.title}
      </span>
      {adcmMeta.synchronization && fieldAttributes && (
        <SynchronizedAttribute
          isSynchronized={fieldAttributes.isSynchronized}
          {...adcmMeta.synchronization}
          onToggle={handleIsSynchronizedChange}
        />
      )}
      {fieldNodeData.value === null && (
        <span className={s.nodeContent__value} data-test="null-stub">
          {nullStub}
        </span>
      )}

      {isExpandable && (
        <IconButton
          icon="chevron"
          size={12}
          className={s.nodeContent__arrow}
          onClick={handleExpandClick}
          data-test="expand-btn"
        />
      )}
    </div>
  );
};

export default NodeWithChildrenContent;

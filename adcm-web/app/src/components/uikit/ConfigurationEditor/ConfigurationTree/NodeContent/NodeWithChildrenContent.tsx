import { useCallback, useRef, useState } from 'react';
import { IconButton, MarkerIcon, Tooltip } from '@uikit';
import { isValueSet } from '@models/json';
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
  const isDeletable = (node.data.type === 'object' || node.data.type === 'array') && node.data.isDeletable;

  const [initialIsActive] = useState(fieldAttributes?.isActive);

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
        if (isSynchronized) {
          onFieldAttributeChange(node.key, { isActive: initialIsActive, isSynchronized });
        } else {
          onFieldAttributeChange(node.key, { ...fieldAttributes, isSynchronized });
        }
      }
    },
    [fieldAttributes, initialIsActive, node.key, onFieldAttributeChange],
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
  const isExpandable = hasChildren && (fieldAttributes?.isActive === undefined ? true : fieldAttributes.isActive);

  return (
    <div className={className} ref={ref}>
      {adcmMeta.activation && fieldAttributes?.isActive !== undefined && (
        <ActivationAttribute
          isActive={fieldAttributes.isActive}
          isAllowChange={adcmMeta.activation.isAllowChange && fieldAttributes.isSynchronized !== true}
          onToggle={handleIsActiveChange}
        />
      )}

      {fieldNodeData.isCleanable && isValueSet(fieldNodeData.value) && (
        <IconButton size={14} icon="g3-clear" onClick={handleClearClick} data-test="clear-btn" />
      )}
      {isDeletable && <IconButton size={14} icon="g3-delete" onClick={handleDeleteClick} data-test="delete-btn" />}
      {error && (
        <Tooltip label={error}>
          <MarkerIcon variant="round" type="alert" size={16} data-test="error" />
        </Tooltip>
      )}
      <span className={s.nodeContent__title} data-test="node-name">
        {node.data.title}
      </span>
      {adcmMeta.synchronization && fieldAttributes?.isSynchronized !== undefined && (
        <SynchronizedAttribute
          isSynchronized={fieldAttributes.isSynchronized}
          {...adcmMeta.synchronization}
          onToggle={handleIsSynchronizedChange}
        />
      )}
      {!isValueSet(fieldNodeData.value) && (
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

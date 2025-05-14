import { useCallback, useRef, useState } from 'react';
import { isValueSet } from '@models/json';
import type { ConfigurationArray, ConfigurationObject, ConfigurationNodeView } from '../../ConfigurationEditor.types';
import type { ChangeConfigurationNodeHandler, ChangeFieldAttributesHandler } from '../ConfigurationTree.types';
import s from '../ConfigurationTree.module.scss';
import cn from 'classnames';
import SynchronizedAttribute from './SyncronizedAttribute/SynchronizedAttribute';
import ActivationAttribute from './ActivationAttribute/ActivationAttribute';
import FieldNodeErrors from './FieldNodeErrors/FieldNodeErrors';
import { nullStub } from '../ConfigurationTree.constants';
import type { FieldErrors } from '@models/adcm';
import IconButton from '@uikit/IconButton/IconButton';
import Tooltip from '@uikit/Tooltip/Tooltip';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import Icon from '@uikit/Icon/Icon';

interface NodeWithChildrenContentProps {
  node: ConfigurationNodeView;
  errors?: FieldErrors;
  isExpanded: boolean;
  onClear: ChangeConfigurationNodeHandler;
  onDelete: ChangeConfigurationNodeHandler;
  onExpand: (isOpen: boolean) => void;
  onFieldAttributeChange: ChangeFieldAttributesHandler;
  onDragStart?: (node: ConfigurationNodeView) => void;
  onDragEnd?: (node: ConfigurationNodeView) => void;
}

const NodeWithChildrenContent = ({
  node,
  isExpanded,
  errors,
  onClear,
  onDelete,
  onExpand,
  onFieldAttributeChange,
  onDragStart,
  onDragEnd,
}: NodeWithChildrenContentProps) => {
  const ref = useRef(null);
  const fieldNodeData = node.data as ConfigurationObject | ConfigurationArray;
  const adcmMeta = node.data.fieldSchema.adcmMeta;
  const fieldAttributes = node.data.fieldAttributes;
  const isDeletable = (node.data.type === 'object' || node.data.type === 'array') && node.data.isDeletable;

  const [initialIsActive] = useState(fieldAttributes?.isActive);
  const [isOverDragHandle, setIsOverDragHandle] = useState(false);

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

  const handleDragHandleMouseEnter = () => {
    setIsOverDragHandle(true);
  };

  const handleDragHandleMouseLeave = () => {
    setIsOverDragHandle(false);
  };

  const handleDragStart = () => {
    onDragStart?.(node);
  };

  const handleDragEnd = () => {
    onDragEnd?.(node);
  };

  const className = cn(s.nodeContent, {
    'is-open': isExpanded,
    'is-failed': errors !== undefined,
  });

  const hasChildren = Boolean(node.children?.length);
  const isExpandable = hasChildren && (fieldAttributes?.isActive === undefined ? true : fieldAttributes.isActive);

  return (
    <div
      ref={ref}
      className={className}
      draggable={isOverDragHandle}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      {fieldNodeData.isDraggable && (
        <Icon
          className={s.nodeContent__dragHandle}
          name="drag-handle"
          onMouseEnter={handleDragHandleMouseEnter}
          onMouseLeave={handleDragHandleMouseLeave}
        />
      )}
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
      {errors && (
        <Tooltip label={<FieldNodeErrors fieldErrors={errors} />}>
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

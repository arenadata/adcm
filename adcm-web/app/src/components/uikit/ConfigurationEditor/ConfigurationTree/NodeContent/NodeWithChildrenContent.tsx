import { useCallback, useRef, useState } from 'react';
import { isValueSet } from '@models/json';
import type { ConfigurationArray, ConfigurationObject, ConfigurationNodeView } from '../../ConfigurationEditor.types';
import type { ChangeConfigurationNodeHandler, ChangeFieldAttributesHandler } from '../ConfigurationTree.types';
import s from '../ConfigurationTree.module.scss';
import st from '../../../CollapseTree2/CollapseNode.module.scss';
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
  onDragEnd?: (node: ConfigurationNodeView, isDropped: boolean) => void;
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

  const handleDragEnd = (event: React.DragEvent<HTMLDivElement>) => {
    const isDropped = event.dataTransfer.dropEffect !== 'none';
    onDragEnd?.(node, isDropped);
  };

  const hasChildren = Boolean(node.children?.length);
  const isExpandable = hasChildren;
  const active = fieldAttributes?.isActive === undefined ? true : fieldAttributes.isActive;

  const className = cn(s.nodeContent, {
    'is-failed': errors !== undefined,
  });

  return (
    <>
      {isExpandable && (
        <IconButton
          icon={isExpanded ? 'remove' : 'g3-add'}
          size={16}
          className={cn(
            s.nodeContent,
            s.nodeContent__button,
            s.expandButton,
            st.expandButton,
            isExpanded ? s.isExpanded : '',
          )}
          onClick={handleExpandClick}
          data-test="expand-btn"
          disabled={!active}
        />
      )}
      <div
        ref={ref}
        className={className}
        draggable={isOverDragHandle}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        {fieldNodeData.isDraggable && (
          <Icon
            size={12}
            className={s.nodeContent__dragHandle}
            name="drag-handle"
            onMouseEnter={handleDragHandleMouseEnter}
            onMouseLeave={handleDragHandleMouseLeave}
          />
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
        {adcmMeta.activation && fieldAttributes?.isActive !== undefined && (
          <ActivationAttribute
            isActive={fieldAttributes.isActive}
            isAllowChange={
              !fieldNodeData.isReadonly && adcmMeta.activation.isAllowChange && !fieldAttributes.isSynchronized
            }
            onToggle={handleIsActiveChange}
          />
        )}
        {errors && (
          <Tooltip label={<FieldNodeErrors fieldErrors={errors} />}>
            <MarkerIcon variant="round" type="alert" size={16} data-test="error" />
          </Tooltip>
        )}
      </div>
      <div className={cn(s.nodeContent__buttonWrapper, st.nodeContent__buttonWrapper)}>
        {fieldNodeData.isCleanable && isValueSet(fieldNodeData.value) && (
          <IconButton
            className={cn(s.nodeContent, s.nodeContent__button)}
            size={16}
            icon="g3-clear"
            onClick={handleClearClick}
            data-test="clear-btn"
          />
        )}
        {isDeletable && (
          <IconButton
            className={cn(s.nodeContent, s.nodeContent__button)}
            size={16}
            icon="g3-delete"
            onClick={handleDeleteClick}
            data-test="delete-btn"
          />
        )}
      </div>
    </>
  );
};

export default NodeWithChildrenContent;

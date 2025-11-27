import { useCallback, useMemo, useRef, useState } from 'react';
import { isValueSet } from '@models/json';
import type {
  ConfigurationArray,
  ConfigurationObject,
  ConfigurationNodeView,
  ConfigurationSelectableObject,
} from '../../../ConfigurationEditor.types';
import type {
  ChangeConfigurationNodeHandler,
  ChangeConfigurationNodeValueHandler,
  ChangeFieldAttributesHandler,
} from '../../ConfigurationTree.types';
import s from '../../ConfigurationTree.module.scss';
import st from '@uikit/CollapseTree2/CollapseNode.module.scss';
import cn from 'classnames';
import SynchronizedAttribute from '../SyncronizedAttribute/SynchronizedAttribute';
import ActivationAttribute from '../ActivationAttribute/ActivationAttribute';
import FieldNodeErrors from '../FieldNodeErrors/FieldNodeErrors';
import { nullStub } from '../../ConfigurationTree.constants';
import type { FieldErrors } from '@models/adcm';
import IconButton from '@uikit/IconButton/IconButton';
import Tooltip from '@uikit/Tooltip/Tooltip';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import Icon from '@uikit/Icon/Icon';
import ObjectSchemaSelect from './ObjectSchemaSelect';

interface NodeWithChildrenContentProps {
  node: ConfigurationNodeView;
  errors?: FieldErrors;
  isExpanded: boolean;
  onClear: ChangeConfigurationNodeHandler;
  onDelete: ChangeConfigurationNodeHandler;
  onChange: ChangeConfigurationNodeValueHandler;
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
  onChange,
  onExpand,
  onFieldAttributeChange,
  onDragStart,
  onDragEnd,
}: NodeWithChildrenContentProps) => {
  const ref = useRef(null);
  const fieldNodeData = node.data as ConfigurationObject | ConfigurationSelectableObject | ConfigurationArray;
  const adcmMeta = fieldNodeData.fieldSchema.adcmMeta;
  const fieldSchema = fieldNodeData.fieldSchema;
  const selectableFieldSchema =
    fieldNodeData.type === 'selectableObject' ? fieldNodeData.selectedFieldSchema : undefined;
  const fieldAttributes = fieldNodeData.fieldAttributes;
  const isDeletable =
    (fieldNodeData.type === 'object' || fieldNodeData.type === 'selectableObject' || fieldNodeData.type === 'array') &&
    fieldNodeData.isDeletable;
  const isResetable =
    !fieldNodeData.isReadonly &&
    fieldNodeData.type === 'array' &&
    fieldNodeData.defaultValue !== undefined &&
    fieldNodeData.value !== fieldNodeData.defaultValue;

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

  const handleResetToDefaultClick = () => {
    onChange(node, fieldNodeData.defaultValue);
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

  const handleSelect = (selection: string | null) => {
    if (selection && node.data.type === 'selectableObject') {
      const defaultValue = node.data.oneOfSchemaDefaults[selection];
      onChange(node, defaultValue);
    }
  };

  const selectionControl = useMemo(() => {
    if (
      fieldNodeData.type !== 'selectableObject' ||
      fieldSchema.discriminator === undefined ||
      selectableFieldSchema === undefined ||
      fieldSchema.oneOf === undefined ||
      fieldSchema.readOnly
    ) {
      return null;
    }

    return <ObjectSchemaSelect data={fieldNodeData} onChange={handleSelect} />;
  }, [fieldSchema, selectableFieldSchema, fieldNodeData.value, handleSelect]);

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
          {fieldNodeData.title}
        </span>
        {adcmMeta?.synchronization && fieldAttributes?.isSynchronized !== undefined && (
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
        {selectionControl}
        {adcmMeta?.activation && fieldAttributes?.isActive !== undefined && (
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
        {isResetable && (
          <IconButton
            className={cn(s.nodeContent, s.nodeContent__button, s.nodeContent__button__resetButton)}
            size={28}
            icon="g1-return"
            onClick={handleResetToDefaultClick}
            data-test="reset-btn"
            title="Reset to default"
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
        {fieldNodeData.fieldSchema.description && (
          <Tooltip label={fieldNodeData.fieldSchema.description} placement="right-start">
            <IconButton
              type="button"
              className={cn(s.nodeContent, s.nodeContent__button)}
              size={18}
              icon="marker-info"
              data-test="description-btn"
            />
          </Tooltip>
        )}
      </div>
    </>
  );
};

export default NodeWithChildrenContent;

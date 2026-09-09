import { useCallback, useEffect, useRef, useMemo, useState } from 'react';
import type { ConfigurationField, ConfigurationNodeView } from '../../ConfigurationEditor.types';
import { emptyStringStub, nullStub, secretStub, whiteSpaceStringStub } from '../ConfigurationTree.constants';
import s from '../ConfigurationTree.module.scss';
import st from '../../../CollapseTree2/CollapseNode.module.scss';
import cn from 'classnames';
import ActivationAttribute from './ActivationAttribute/ActivationAttribute';
import SynchronizedAttribute from './SyncronizedAttribute/SynchronizedAttribute';
import FieldNodeErrors from './FieldNodeErrors/FieldNodeErrors';
import type {
  ChangeConfigurationNodeHandler,
  ChangeConfigurationNodeValueHandler,
  ChangeFieldAttributesHandler,
} from '../ConfigurationTree.types';
import { isPrimitiveValueSet } from '@models/json';
import { hasFieldDefaultValue, resolveFieldDefaultValue } from '../ConfigurationTree.utils';
import type { FieldErrors } from '@models/adcm';
import { isWhiteSpaceOnly } from '@utils/validationsUtils';
import IconButton from '@uikit/IconButton/IconButton';
import Tooltip from '@uikit/Tooltip/Tooltip';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import Icon from '@uikit/Icon/Icon';
import { useClipboardCopy } from '@hooks';
import InlinePrimitiveFieldControl from '../../InlinePrimitiveFieldControl/InlinePrimitiveFieldControl';
import { useInlineField } from './useInlineField';

interface FieldNodeContentProps {
  node: ConfigurationNodeView;
  errors?: FieldErrors;
  shouldFocus?: boolean;
  onFocusHandled?: () => void;
  onClick: ChangeConfigurationNodeHandler;
  onClear: ChangeConfigurationNodeHandler;
  onDelete: ChangeConfigurationNodeHandler;
  onChange: ChangeConfigurationNodeValueHandler;
  onFieldAttributeChange: ChangeFieldAttributesHandler;
  onDragStart?: (node: ConfigurationNodeView) => void;
  onDragEnd?: (node: ConfigurationNodeView, isDropped: boolean) => void;
}

const FieldNodeContent = ({
  node,
  errors,
  shouldFocus = false,
  onFocusHandled,
  onClick,
  onClear,
  onDelete,
  onChange,
  onFieldAttributeChange,
  onDragStart,
  onDragEnd,
}: FieldNodeContentProps) => {
  const ref = useRef(null);
  const fieldNodeData = node.data as ConfigurationField;
  const adcmMeta = fieldNodeData.fieldSchema.adcmMeta;
  const fieldAttributes = node.data.fieldAttributes;

  const [initialIsActive] = useState(fieldAttributes?.isActive);
  const [isOverDragHandle, setIsOverDragHandle] = useState(false);
  const [_, copyToClipboard] = useClipboardCopy();

  const inlineField = useInlineField({ node, fieldNodeData, onChange });

  const shouldAutoFocusInlineField = shouldFocus && inlineField.isEditable && !isPrimitiveValueSet(fieldNodeData.value);

  useEffect(() => {
    if (!shouldFocus) {
      return;
    }

    if (inlineField.isEditable) {
      onFocusHandled?.();
      return;
    }

    if (!isPrimitiveValueSet(fieldNodeData.value)) {
      onClick(node, ref);
    }

    onFocusHandled?.();
  }, [shouldFocus, inlineField.isEditable, fieldNodeData.value, node, onClick, onFocusHandled]);

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
        if (isSynchronized) {
          onFieldAttributeChange(node.key, { isActive: initialIsActive, isSynchronized });
        } else {
          onFieldAttributeChange(node.key, { ...fieldAttributes, isSynchronized });
        }
      }
    },
    [fieldAttributes, initialIsActive, node.key, onFieldAttributeChange],
  );

  const handleClick = () => {
    onClick(node, ref);
  };

  const handleClearClick = () => {
    onClear(node, ref);
  };

  const handleDeleteClick = () => {
    onDelete(node, ref);
  };

  const handleResetToDefaultClick = () => {
    onChange(node, resolveFieldDefaultValue(fieldNodeData));
  };

  const handleActionMouseDown = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
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

  const handleCopyNodeValueClick = () => {
    if (fieldNodeData !== undefined && fieldNodeData !== null) {
      copyToClipboard(displayValue.toString());
    }
  };
  const displayValue: string | number | boolean = useMemo(() => {
    if (!isPrimitiveValueSet(fieldNodeData.value)) {
      return nullStub;
    }

    if (fieldNodeData.fieldSchema.enum) {
      if (adcmMeta?.enumExtra?.labels) {
        const valueIndex = fieldNodeData.fieldSchema.enum?.indexOf(fieldNodeData.value);
        if (valueIndex !== undefined) {
          return adcmMeta.enumExtra.labels[valueIndex];
        }
      }
    }

    if (fieldNodeData.value === '') {
      return emptyStringStub;
    }

    if (isWhiteSpaceOnly(fieldNodeData.value.toString())) {
      return whiteSpaceStringStub;
    }

    if (adcmMeta?.isSecret) {
      return secretStub;
    }

    return fieldNodeData.value.toString();
  }, [adcmMeta?.isSecret, adcmMeta?.enumExtra, fieldNodeData.fieldSchema.enum, fieldNodeData.value]);

  const className = cn(s.nodeContent, {
    'is-failed': errors !== undefined,
    [s.nodeContent_inline]: inlineField.showInlineControl,
    [s.nodeContent_inlineString]: inlineField.isStringField,
    'is-inline-string': inlineField.isStringField,
  });

  return (
    <>
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
            name="drag-handle"
            className={s.nodeContent__dragHandle}
            onMouseEnter={handleDragHandleMouseEnter}
            onMouseLeave={handleDragHandleMouseLeave}
          />
        )}
        <div className={s.nodeContent__title} data-test="node-name">
          {`${fieldNodeData.title}: `}
        </div>
        {adcmMeta?.synchronization && fieldAttributes?.isSynchronized !== undefined && (
          <SynchronizedAttribute
            isSynchronized={fieldAttributes.isSynchronized}
            {...adcmMeta.synchronization}
            onToggle={handleIsSynchronizedChange}
          />
        )}
        <div
          className={cn(s.nodeContent__value, {
            [s.nodeContent__value_inline]: inlineField.showInlineControl,
            [s.nodeContent__value_inlineString]: inlineField.isStringField,
          })}
          style={inlineField.valueStyle}
          data-test="node-value"
          onClick={inlineField.isEditable ? inlineField.onValueClick : handleClick}
        >
          {inlineField.showInlineControl ? (
            <InlinePrimitiveFieldControl
              fieldSchema={fieldNodeData.fieldSchema}
              value={fieldNodeData.value}
              isReadonly={fieldNodeData.isReadonly}
              autoFocus={shouldAutoFocusInlineField}
              onChange={inlineField.onChange}
            />
          ) : (
            displayValue
          )}
        </div>
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
            <MarkerIcon className={s.nodeContent__errorIcon} variant="round" type="alert" size={16} data-test="error" />
          </Tooltip>
        )}
      </div>
      <div className={cn(s.nodeContent__buttonWrapper, st.nodeContent__buttonWrapper)}>
        {!adcmMeta?.isSecret && (
          <IconButton
            className={cn(s.nodeContent, s.nodeContent__button)}
            size={16}
            icon="g1-copy"
            onMouseDown={handleActionMouseDown}
            onClick={handleCopyNodeValueClick}
            data-test="copy-btn"
            title="Copy value"
          />
        )}
        {fieldNodeData.isCleanable && isPrimitiveValueSet(fieldNodeData.value) && (
          <IconButton
            className={cn(s.nodeContent, s.nodeContent__button)}
            size={16}
            icon="g3-clear"
            onMouseDown={handleActionMouseDown}
            onClick={handleClearClick}
            data-test="clear-btn"
          />
        )}
        {!fieldNodeData.isReadonly &&
          hasFieldDefaultValue(fieldNodeData) &&
          fieldNodeData.value !== resolveFieldDefaultValue(fieldNodeData) && (
            <IconButton
              className={cn(s.nodeContent, s.nodeContent__button, s.nodeContent__button__resetButton)}
              size={28}
              icon="g1-return"
              onMouseDown={handleActionMouseDown}
              onClick={handleResetToDefaultClick}
              data-test="reset-btn"
              title="Reset to default"
            />
          )}
        {fieldNodeData.isDeletable && (
          <IconButton
            className={cn(s.nodeContent, s.nodeContent__button)}
            size={16}
            icon="g3-delete"
            onMouseDown={handleActionMouseDown}
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
              onMouseDown={handleActionMouseDown}
              data-test="description-btn"
            />
          </Tooltip>
        )}
      </div>
    </>
  );
};

export default FieldNodeContent;

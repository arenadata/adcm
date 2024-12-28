import { useCallback, useRef, useMemo, useState } from 'react';
import type { ConfigurationField, ConfigurationNodeView } from '../../ConfigurationEditor.types';
import { emptyStringStub, nullStub, secretStub, whiteSpaceStringStub } from '../ConfigurationTree.constants';
import s from '../ConfigurationTree.module.scss';
import cn from 'classnames';
import ActivationAttribute from './ActivationAttribute/ActivationAttribute';
import SynchronizedAttribute from './SyncronizedAttribute/SynchronizedAttribute';
import FieldNodeErrors from './FieldNodeErrors/FieldNodeErrors';
import type { ChangeConfigurationNodeHandler, ChangeFieldAttributesHandler } from '../ConfigurationTree.types';
import { isPrimitiveValueSet } from '@models/json';
import type { FieldErrors } from '@models/adcm';
import { isWhiteSpaceOnly } from '@utils/validationsUtils';
import IconButton from '@uikit/IconButton/IconButton';
import Tooltip from '@uikit/Tooltip/Tooltip';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';

interface FieldNodeContentProps {
  node: ConfigurationNodeView;
  errors?: FieldErrors;
  onClick: ChangeConfigurationNodeHandler;
  onClear: ChangeConfigurationNodeHandler;
  onDelete: ChangeConfigurationNodeHandler;
  onFieldAttributeChange: ChangeFieldAttributesHandler;
}

const FieldNodeContent = ({
  node,
  errors,
  onClick,
  onClear,
  onDelete,
  onFieldAttributeChange,
}: FieldNodeContentProps) => {
  const ref = useRef(null);
  const fieldNodeData = node.data as ConfigurationField;
  const adcmMeta = fieldNodeData.fieldSchema.adcmMeta;
  const fieldAttributes = node.data.fieldAttributes;

  const [initialIsActive] = useState(fieldAttributes?.isActive);

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

  const className = cn(s.nodeContent, {
    'is-failed': errors !== undefined,
  });

  const value: string | number | boolean = useMemo(() => {
    if (!isPrimitiveValueSet(fieldNodeData.value)) {
      return nullStub;
    }

    if (fieldNodeData.fieldSchema.enum) {
      if (fieldNodeData.fieldSchema.adcmMeta.enumExtra?.labels) {
        const valueIndex = fieldNodeData.fieldSchema.enum?.indexOf(fieldNodeData.value);
        if (valueIndex !== undefined) {
          return fieldNodeData.fieldSchema.adcmMeta.enumExtra.labels[valueIndex];
        }
      }
    }

    if (fieldNodeData.value === '') {
      return emptyStringStub;
    }

    if (isWhiteSpaceOnly(fieldNodeData.value.toString())) {
      return whiteSpaceStringStub;
    }

    if (adcmMeta.isSecret) {
      return secretStub;
    }

    return fieldNodeData.value.toString();
  }, [
    adcmMeta.isSecret,
    fieldNodeData.fieldSchema.adcmMeta.enumExtra,
    fieldNodeData.fieldSchema.enum,
    fieldNodeData.value,
  ]);

  return (
    <div ref={ref} className={className}>
      {adcmMeta.activation && fieldAttributes?.isActive !== undefined && (
        <ActivationAttribute
          isActive={fieldAttributes.isActive}
          isAllowChange={adcmMeta.activation.isAllowChange && fieldAttributes.isSynchronized !== true}
          onToggle={handleIsActiveChange}
        />
      )}
      {fieldNodeData.isCleanable && isPrimitiveValueSet(fieldNodeData.value) && (
        <IconButton size={14} icon="g3-clear" onClick={handleClearClick} data-test="clear-btn" />
      )}
      {fieldNodeData.isDeletable && (
        <IconButton size={14} icon="g3-delete" onClick={handleDeleteClick} data-test="delete-btn" />
      )}
      {errors && (
        <Tooltip label={<FieldNodeErrors fieldErrors={errors} />}>
          <MarkerIcon variant="round" type="alert" size={16} data-test="error" />
        </Tooltip>
      )}
      <span className={s.nodeContent__title} data-test="node-name">
        {`${fieldNodeData.title}: `}
      </span>
      {adcmMeta.synchronization && fieldAttributes?.isSynchronized !== undefined && (
        <SynchronizedAttribute
          isSynchronized={fieldAttributes.isSynchronized}
          {...adcmMeta.synchronization}
          onToggle={handleIsSynchronizedChange}
        />
      )}
      <span className={s.nodeContent__value} data-test="node-value" onClick={handleClick}>
        {value}
      </span>
    </div>
  );
};

export default FieldNodeContent;

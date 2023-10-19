import { useState, useMemo, useCallback } from 'react';
import ConfigurationEditorDialog from '../ConfigurationEditorDialog/ConfigurationEditorDialog';
import { Node } from '@uikit/CollapseTree2/CollapseNode.types';
import { JSONPrimitive } from '@models/json';
import { ConfigurationField, ConfigurationNode } from '../../ConfigurationEditor.types';
import EnumControl from '../FieldControls/EnumControl';
import StringControl from '../FieldControls/StringControl';
import MultilineStringControl from '../FieldControls/MultilineStringControl';
import BooleanControl from '../FieldControls/BooleanControl';
import NumberControl from '../FieldControls/NumberControl';
import SecretControl from '../FieldControls/SecretControl';

export interface ConfigurationEditInputFieldDialogProps {
  node: ConfigurationNode;
  triggerRef: React.RefObject<HTMLElement>;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onChange: (node: ConfigurationNode, value: JSONPrimitive) => void;
}

const multilineWidthProps = { width: '100%', maxWidth: '1280px' };

const EditConfigurationFieldDialog = ({
  node,
  triggerRef,
  isOpen,
  onOpenChange,
  onChange,
}: ConfigurationEditInputFieldDialogProps) => {
  const fieldNode = node as Node<ConfigurationField>;
  const adcmMeta = fieldNode.data.fieldSchema.adcmMeta;
  const attributes = fieldNode.data.fieldAttributes;

  const isParentSynchronized = fieldNode.data.parentNode.data.fieldAttributes?.isSynchronized === true;
  const isSynchronized = attributes?.isSynchronized === true;

  const [value, setValue] = useState<JSONPrimitive>(fieldNode.data.value);
  const [isApplyDisabled, setIsApplyDisabled] = useState(true);

  const handleOpenChange = (isOpen: boolean) => {
    onOpenChange(isOpen);
  };

  const handleValueChange = useCallback((value: JSONPrimitive, isValid = true) => {
    setValue(value as JSONPrimitive);
    setIsApplyDisabled(!isValid);
  }, []);

  const handleCancel = () => {
    onOpenChange(false);
  };

  const handleApply = () => {
    if (value !== fieldNode.data.value) {
      if (value === '' && adcmMeta.nullValue !== undefined) {
        onChange(fieldNode, adcmMeta.nullValue as JSONPrimitive);
      } else {
        onChange(fieldNode, value);
      }
    }
    onOpenChange(false);
  };

  const Control = useMemo(() => {
    if (fieldNode.data.fieldSchema.enum) {
      return EnumControl;
    }

    switch (fieldNode.data.fieldSchema.type) {
      case 'string': {
        const isMultiline = adcmMeta.stringExtra?.isMultiline;
        if (isMultiline) {
          return MultilineStringControl;
        } else {
          if (adcmMeta.isSecret) {
            return SecretControl;
          } else {
            return StringControl;
          }
        }
      }
      case 'integer':
      case 'number': {
        return NumberControl;
      }
      case 'boolean': {
        return BooleanControl;
      }
      default: {
        return null;
      }
    }
  }, [
    fieldNode.data.fieldSchema.enum,
    fieldNode.data.fieldSchema.type,
    adcmMeta.stringExtra?.isMultiline,
    adcmMeta.isSecret,
  ]);

  const widthProps = adcmMeta.stringExtra?.isMultiline ? multilineWidthProps : undefined;

  return (
    <ConfigurationEditorDialog
      {...widthProps}
      triggerRef={triggerRef}
      isOpen={isOpen}
      onCancel={handleCancel}
      onApply={handleApply}
      isApplyDisabled={isApplyDisabled}
      onOpenChange={handleOpenChange}
    >
      {Control && (
        <Control
          fieldName={fieldNode.data.title}
          fieldSchema={fieldNode.data.fieldSchema}
          value={value}
          isReadonly={fieldNode.data.isReadonly || isSynchronized || isParentSynchronized}
          onChange={handleValueChange}
        />
      )}
    </ConfigurationEditorDialog>
  );
};

export default EditConfigurationFieldDialog;

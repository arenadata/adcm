import { useState, useMemo, useCallback } from 'react';
import ConfigurationEditorDialog from '../ConfigurationEditorDialog/ConfigurationEditorDialog';
import type { Node } from '@uikit/CollapseTree2/CollapseNode.types';
import type { JSONPrimitive } from '@models/json';
import type { ConfigurationField, ConfigurationNodeView } from '../../ConfigurationEditor.types';
import EnumControl from '../FieldControls/EnumControl';
import StringControl from '../FieldControls/StringControls/StringControl';
import MultilineStringControl from '../FieldControls/StringControls/MultilineStringControl';
import BooleanControl from '../FieldControls/BooleanControl';
import NumberControl from '../FieldControls/NumberControl';
import SecretControl from '../FieldControls/StringControls/SecretControl';

export interface ConfigurationEditInputFieldDialogProps {
  node: ConfigurationNodeView;
  triggerRef: React.RefObject<HTMLElement>;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onChange: (node: ConfigurationNodeView, value: JSONPrimitive) => void;
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

  const [value, setValue] = useState<JSONPrimitive>(fieldNode.data.value);
  const [isValueValid, setIsValueValid] = useState(true);
  const [isValueBeingEdited, setIsValueBeingEdited] = useState(false);

  const handleOpenChange = (isOpen: boolean) => {
    onOpenChange(isOpen);
  };

  const handleValueChange = useCallback(
    (value: JSONPrimitive, isValid = true) => {
      setValue(value as JSONPrimitive);
      setIsValueValid(isValid);
      if (value !== fieldNode.data.value) {
        setIsValueBeingEdited(true);
      }
    },
    [fieldNode.data.value],
  );

  const handleCancel = () => {
    onOpenChange(false);
  };

  const handleApply = () => {
    if (value !== fieldNode.data.value) {
      onChange(fieldNode, value);
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
      isApplyDisabled={!isValueValid || fieldNode.data.isReadonly || !isValueBeingEdited}
      onOpenChange={handleOpenChange}
    >
      {Control && (
        <Control
          fieldName={fieldNode.data.title}
          fieldSchema={fieldNode.data.fieldSchema}
          value={value}
          isReadonly={fieldNode.data.isReadonly}
          onChange={handleValueChange}
          onApply={handleApply}
        />
      )}
    </ConfigurationEditorDialog>
  );
};

export default EditConfigurationFieldDialog;

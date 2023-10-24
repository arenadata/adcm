import { useState } from 'react';
import { FormField, Input } from '@uikit';
import ConfigurationEditorDialog from '../ConfigurationEditorDialog/ConfigurationEditorDialog';
import { ConfigurationNode } from '../../ConfigurationEditor.types';
import { JSONPrimitive } from '@models/json';
import StringControl from '../FieldControls/StringControl';
import SecretControl from '../FieldControls/SecretControl';
import s from './AddConfigurationFieldDialog.module.scss';

export interface AddConfigurationFieldDialogProps {
  node: ConfigurationNode;
  triggerRef: React.RefObject<HTMLElement>;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onAddField: (node: ConfigurationNode, fieldName: string, value: JSONPrimitive) => void;
}

const AddConfigurationFieldDialog = ({
  node,
  triggerRef,
  isOpen,
  onOpenChange,
  onAddField,
}: AddConfigurationFieldDialogProps) => {
  const [fieldName, setFieldName] = useState('');
  const [value, setValue] = useState('');
  const [isValueValid, setIsValueValid] = useState(false);

  const handleFieldNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFieldName(e.target.value);
  };

  const handleChange = (value: JSONPrimitive, isValid = true) => {
    setValue(value as string);
    setIsValueValid(isValid);
  };

  const handleOpenChange = (isOpen: boolean) => {
    onOpenChange(isOpen);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  const handleApply = () => {
    onAddField(node, fieldName, value);
    onOpenChange(false);
  };

  const inputClassName = s.addConfigurationFieldDialog__input;

  return (
    <ConfigurationEditorDialog
      triggerRef={triggerRef}
      isOpen={isOpen}
      isApplyDisabled={!isValueValid || fieldName === ''}
      onOpenChange={handleOpenChange}
      onCancel={handleCancel}
      onApply={handleApply}
    >
      <div className={s.addConfigurationFieldDialog__content}>
        <FormField label="Enter field name">
          <Input className={inputClassName} value={fieldName} onChange={handleFieldNameChange} />
        </FormField>

        {node.data.fieldSchema.adcmMeta.isSecret ? (
          <SecretControl
            fieldName="Enter secret"
            value={value}
            fieldSchema={node.data.fieldSchema}
            isReadonly={false}
            onChange={handleChange}
          />
        ) : (
          <StringControl
            fieldName="Enter field value"
            value={value}
            fieldSchema={node.data.fieldSchema}
            isReadonly={false}
            onChange={handleChange}
          />
        )}
      </div>
    </ConfigurationEditorDialog>
  );
};

export default AddConfigurationFieldDialog;

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

  const handleFieldNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFieldName(e.target.value);
  };

  const handleChange = (value: JSONPrimitive) => {
    setValue(value as string);
  };

  const handleOpenChange = (isOpen: boolean) => {
    onAddField(node, fieldName, value);
    onOpenChange(isOpen);
  };

  const inputClassName = s.addConfigurationFieldDialog__input;

  return (
    <ConfigurationEditorDialog isOpen={isOpen} onOpenChange={handleOpenChange} triggerRef={triggerRef}>
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

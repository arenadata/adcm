import { useState } from 'react';
import ConfigurationEditorDialog from '../ConfigurationEditorDialog/ConfigurationEditorDialog';
import type { Node } from '@uikit/CollapseTree2/CollapseNode.types';
import type { JSONPrimitive } from '@models/json';
import type { ConfigurationField, ConfigurationNodeView } from '../../ConfigurationEditor.types';
import StringControl from '../FieldControls/StringControls/StringControl';
import SecretControl from '../FieldControls/StringControls/SecretControl';
import s from './AddConfigurationFieldDialog.module.scss';
import FormField from '@uikit/FormField/FormField';
import Input from '@uikit/Input/Input';

export interface AddConfigurationFieldDialogProps {
  node: ConfigurationNodeView;
  triggerRef: React.RefObject<HTMLElement>;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onAddField: (node: ConfigurationNodeView, fieldName: string, value: JSONPrimitive) => void;
}

const AddConfigurationFieldDialog = ({
  node,
  triggerRef,
  isOpen,
  onOpenChange,
  onAddField,
}: AddConfigurationFieldDialogProps) => {
  const fieldNode = node as Node<ConfigurationField>;
  const adcmMeta = fieldNode.data.fieldSchema.adcmMeta;

  const [fieldName, setFieldName] = useState('');
  const [value, setValue] = useState('');
  const [isValueValid, setIsValueValid] = useState(true);

  const handleOpenChange = (isOpen: boolean) => {
    onOpenChange(isOpen);
  };

  const handleFieldNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFieldName(e.target.value);
  };

  const handleValueChange = (value: JSONPrimitive, isValid = true) => {
    setValue(value as string);
    setIsValueValid(isValid);
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

        {adcmMeta.isSecret ? (
          <SecretControl
            fieldName="Enter secret"
            value={value}
            fieldSchema={node.data.fieldSchema}
            defaultValue={fieldNode.data.defaultValue}
            isReadonly={false}
            onChange={handleValueChange}
            onApply={handleApply}
          />
        ) : (
          <StringControl
            fieldName="Enter field value"
            value={value}
            fieldSchema={node.data.fieldSchema}
            defaultValue={fieldNode.data.defaultValue}
            isReadonly={false}
            onChange={handleValueChange}
            onApply={handleApply}
          />
        )}
      </div>
    </ConfigurationEditorDialog>
  );
};

export default AddConfigurationFieldDialog;

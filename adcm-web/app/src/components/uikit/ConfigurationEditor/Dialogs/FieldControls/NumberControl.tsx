import InputNumber from '@uikit/InputNumber/InputNumber';
import ConfigurationField from './ConfigurationField';
import { SingleSchemaDefinition } from '@models/adcm';
import { JSONPrimitive } from '@models/json';

export interface NumberControlProps {
  fieldName: string;
  value: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (value: JSONPrimitive) => void;
  onApply: () => void;
}

const NumberControl = ({ fieldName, fieldSchema, value, isReadonly, onChange, onApply }: NumberControlProps) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.value === '') {
      onChange('');
    } else {
      onChange(e.target.valueAsNumber);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Enter') {
      onApply();
    }
  };

  return (
    <ConfigurationField label={fieldName} fieldSchema={fieldSchema} disabled={isReadonly} onResetToDefault={onChange}>
      <InputNumber
        value={value as number}
        disabled={isReadonly}
        min={fieldSchema.minimum}
        max={fieldSchema.maximum}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
      />
    </ConfigurationField>
  );
};

export default NumberControl;

import Input from '@uikit/Input/Input';
import InputWithAutocomplete from '@uikit/InputWithAutocomplete/InputWithAutocomplete';
import ConfigurationField from './ConfigurationField';
import { SingleSchemaDefinition } from '@models/adcm';
import { JSONPrimitive } from '@models/json';

export interface StringControlProps {
  fieldName: string;
  value: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (value: JSONPrimitive) => void;
}

const StringControl = ({ fieldName, value, fieldSchema, isReadonly, onChange }: StringControlProps) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value);
  };

  const stringValue = value as string;

  return (
    <ConfigurationField label={fieldName} fieldSchema={fieldSchema} isReadonly={isReadonly} onChange={onChange}>
      {fieldSchema.adcmMeta.stringExtra?.suggestions ? (
        <InputWithAutocomplete
          value={stringValue}
          readOnly={isReadonly}
          suggestions={fieldSchema.adcmMeta.stringExtra.suggestions}
          onChange={handleChange}
        />
      ) : (
        <Input value={stringValue} readOnly={isReadonly} onChange={handleChange} />
      )}
    </ConfigurationField>
  );
};

export default StringControl;

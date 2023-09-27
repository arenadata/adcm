import Input from '@uikit/Input/Input';
import InputWithAutocomplete from '@uikit/InputWithAutocomplete/InputWithAutocomplete';
import ConfigurationField from './ConfigurationField';
import { SingleSchemaDefinition } from '@models/adcm';
import { JSONPrimitive } from '@models/json';

export interface StringControlProps {
  fieldName: string;
  value: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  onChange: (value: JSONPrimitive) => void;
}

const StringControl = ({ fieldName, value, fieldSchema, onChange }: StringControlProps) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value);
  };

  const stringValue = value as string;

  return (
    <ConfigurationField label={fieldName} fieldSchema={fieldSchema} onChange={onChange}>
      {fieldSchema.adcmMeta.stringExtra?.suggestions ? (
        <InputWithAutocomplete
          value={stringValue}
          onChange={handleChange}
          suggestions={fieldSchema.adcmMeta.stringExtra.suggestions}
        />
      ) : (
        <Input value={stringValue} onChange={handleChange} />
      )}
    </ConfigurationField>
  );
};

export default StringControl;

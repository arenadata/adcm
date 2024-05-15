import { useState } from 'react';
import Input from '@uikit/Input/Input';
import InputWithAutocomplete from '@uikit/InputWithAutocomplete/InputWithAutocomplete';
import ConfigurationField from '../ConfigurationField';
import { SingleSchemaDefinition } from '@models/adcm';
import { JSONPrimitive } from '@models/json';
import { validate } from './StringControls.utils';

export interface StringControlProps {
  fieldName: string;
  value: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (value: JSONPrimitive, isValid?: boolean) => void;
}

const StringControl = ({ fieldName, value, fieldSchema, isReadonly, onChange }: StringControlProps) => {
  const [error, setError] = useState<string | undefined>(undefined);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const error = validate(event.target.value, fieldSchema);

    setError(error);
    onChange(event.target.value, error === undefined);
  };

  const stringValue = value as string;

  return (
    <ConfigurationField
      label={fieldName}
      fieldSchema={fieldSchema}
      disabled={isReadonly}
      onResetToDefault={onChange}
      error={error}
    >
      {fieldSchema.adcmMeta.stringExtra?.suggestions ? (
        <InputWithAutocomplete
          value={stringValue}
          disabled={isReadonly}
          suggestions={fieldSchema.adcmMeta.stringExtra.suggestions}
          onChange={handleChange}
        />
      ) : (
        <Input value={stringValue} disabled={isReadonly} onChange={handleChange} />
      )}
    </ConfigurationField>
  );
};

export default StringControl;

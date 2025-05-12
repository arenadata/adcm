import { useState } from 'react';
import Input from '@uikit/Input/Input';
import InputWithAutocomplete from '@uikit/InputWithAutocomplete/InputWithAutocomplete';
import ConfigurationField from '../ConfigurationField';
import type { SingleSchemaDefinition } from '@models/adcm';
import type { JSONPrimitive } from '@models/json';
import { validate } from './StringControls.utils';

export interface StringControlProps {
  fieldName: string;
  value: JSONPrimitive;
  defaultValue: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (value: JSONPrimitive, isValid?: boolean) => void;
  onApply: () => void;
}

const StringControl = ({
  fieldName,
  value,
  fieldSchema,
  defaultValue,
  isReadonly,
  onChange,
  onApply,
}: StringControlProps) => {
  const [error, setError] = useState<string | undefined>(undefined);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const error = validate(event.target.value, fieldSchema);

    setError(error);
    onChange(event.target.value, error === undefined);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (error === undefined && event.key === 'Enter') {
      onApply();
    }
  };

  const stringValue = (value as string) ?? '';

  return (
    <ConfigurationField
      label={fieldName}
      fieldSchema={fieldSchema}
      defaultValue={defaultValue}
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
          onKeyDown={handleKeyDown}
        />
      ) : (
        <Input value={stringValue} disabled={isReadonly} onChange={handleChange} onKeyDown={handleKeyDown} />
      )}
    </ConfigurationField>
  );
};

export default StringControl;

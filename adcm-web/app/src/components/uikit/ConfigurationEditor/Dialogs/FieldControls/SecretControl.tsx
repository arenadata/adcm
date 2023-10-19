import { useState, useEffect } from 'react';
import InputPassword from '@uikit/InputPassword/InputPassword';
import ConfigurationField from './ConfigurationField';
import { SingleSchemaDefinition } from '@models/adcm';
import { JSONPrimitive } from '@models/json';

const mismatchErrorText = 'Please, make sure your secrets match';

export interface StringControlProps {
  fieldName: string;
  value: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (value: JSONPrimitive, isValid?: boolean) => void;
}

const SecretControl = ({ fieldName, fieldSchema, value, isReadonly, onChange }: StringControlProps) => {
  const [secret, setSecret] = useState(value as string);
  const [confirm, setConfirm] = useState(value as string);
  const [error, setError] = useState<string | undefined>(undefined);

  const handleSecretChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSecret(event.target.value);
  };

  const handleConfirmChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setConfirm(event.target.value);
  };

  useEffect(() => {
    const areEqual = secret === confirm;
    onChange(secret, areEqual && secret !== '');
    setError(!areEqual ? mismatchErrorText : undefined);
  }, [confirm, onChange, secret]);

  return (
    <>
      <ConfigurationField
        label={fieldName}
        fieldSchema={fieldSchema}
        error={error}
        isReadonly={isReadonly}
        onChange={onChange}
      >
        <InputPassword value={secret} readOnly={isReadonly} onChange={handleSecretChange} />
      </ConfigurationField>
      {!isReadonly && (
        <ConfigurationField
          label="Confirm"
          fieldSchema={fieldSchema}
          error={error}
          isReadonly={isReadonly}
          onChange={onChange}
        >
          <InputPassword value={confirm} onChange={handleConfirmChange} />
        </ConfigurationField>
      )}
    </>
  );
};

export default SecretControl;

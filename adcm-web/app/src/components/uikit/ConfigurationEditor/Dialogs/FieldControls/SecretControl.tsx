import { useState, useEffect, memo } from 'react';
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
  onChange: (value: JSONPrimitive) => void;
}

const SecretControl = memo(({ fieldName, fieldSchema, value, isReadonly, onChange }: StringControlProps) => {
  const [secret, setSecret] = useState(value as string);
  const [confirm, setConfirm] = useState(value as string);
  const [error, setError] = useState<string | undefined>(undefined);

  const handleFocus = () => {
    if (!isReadonly) {
      setSecret('');
      setConfirm('');
    }
  };

  const handleSecretChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setSecret(event.target.value);
  };

  const handleConfirmChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setConfirm(event.target.value);
  };

  useEffect(() => {
    if (secret === confirm) {
      onChange(secret);
    }
  }, [confirm, onChange, secret]);

  const handleConfirmBlur = () => {
    setError(secret !== confirm ? mismatchErrorText : undefined);
  };

  return (
    <>
      <ConfigurationField
        label={fieldName}
        fieldSchema={fieldSchema}
        error={error}
        isReadonly={isReadonly}
        onChange={onChange}
      >
        <InputPassword
          value={secret}
          readOnly={isReadonly}
          onChange={handleSecretChange}
          onFocus={handleFocus}
          onBlur={handleConfirmBlur}
        />
      </ConfigurationField>
      {!isReadonly && (
        <ConfigurationField
          label="Confirm"
          fieldSchema={fieldSchema}
          error={error}
          isReadonly={isReadonly}
          onChange={onChange}
        >
          <InputPassword value={confirm} onChange={handleConfirmChange} onBlur={handleConfirmBlur} />
        </ConfigurationField>
      )}
    </>
  );
});

export default SecretControl;

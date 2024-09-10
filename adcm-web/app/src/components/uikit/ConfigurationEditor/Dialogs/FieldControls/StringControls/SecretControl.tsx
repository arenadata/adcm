import { useState, useEffect } from 'react';
import InputPassword from '@uikit/InputPassword/InputPassword';
import ConfigurationField from '../ConfigurationField';
import { SingleSchemaDefinition } from '@models/adcm';
import { JSONPrimitive } from '@models/json';
import { validate } from './StringControls.utils';

const mismatchErrorText = 'Please, make sure your secrets match';

export interface StringControlProps {
  fieldName: string;
  value: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (value: JSONPrimitive, isValid?: boolean) => void;
  onApply: () => void;
}

const SecretControl = ({ fieldName, fieldSchema, value, isReadonly, onChange, onApply }: StringControlProps) => {
  const [secret, setSecret] = useState(value as string);
  const [confirm, setConfirm] = useState(value as string);
  const [secretError, setSecretError] = useState<string | undefined>(undefined);
  const [confirmError, setConfirmError] = useState<string | undefined>(undefined);

  const handleSecretChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const error = validate(event.target.value, fieldSchema);
    setSecretError(error);
    setSecret(event.target.value);
  };

  const handleConfirmChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setConfirm(event.target.value);
  };

  useEffect(() => {
    const areEqual = secret === confirm;
    onChange(secret, areEqual && secretError === undefined);
    setConfirmError(!areEqual ? mismatchErrorText : undefined);
  }, [secret, secretError, confirm, onChange]);

  const handleResetToDefault = (defaultValue: JSONPrimitive) => {
    onChange(defaultValue, true);
    setSecret(defaultValue as string);
    setConfirm(defaultValue as string);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    const areEqual = secret === confirm;
    if (areEqual && event.key === 'Enter') {
      onApply();
    }
  };

  return (
    <form>
      <ConfigurationField
        label={fieldName}
        fieldSchema={fieldSchema}
        error={secretError}
        disabled={isReadonly}
        onResetToDefault={handleResetToDefault}
      >
        <InputPassword
          tabIndex={0}
          value={secret}
          disabled={isReadonly}
          onChange={handleSecretChange}
          onKeyDown={handleKeyDown}
        />
      </ConfigurationField>
      {!isReadonly && (
        <ConfigurationField
          label="Confirm"
          fieldSchema={fieldSchema}
          error={confirmError}
          disabled={isReadonly}
          onResetToDefault={handleResetToDefault}
        >
          <InputPassword
            tabIndex={0}
            value={confirm}
            disabled={isReadonly}
            onChange={handleConfirmChange}
            onKeyDown={handleKeyDown}
          />
        </ConfigurationField>
      )}
    </form>
  );
};

export default SecretControl;

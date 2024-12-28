import Checkbox from '@uikit/Checkbox/Checkbox';
import ConfigurationField from './ConfigurationField';
import type { JSONPrimitive } from '@models/json';
import type { SingleSchemaDefinition } from '@models/adcm';
import s from './ConfigurationField.module.scss';

export interface BooleanControlProps {
  fieldName: string;
  value: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (value: JSONPrimitive) => void;
  onApply: () => void;
}

const BooleanControl = ({ fieldName, fieldSchema, value, isReadonly, onChange, onApply }: BooleanControlProps) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.checked);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Enter') {
      onApply();
    }
  };

  return (
    <ConfigurationField label={fieldName} fieldSchema={fieldSchema} disabled={isReadonly} onResetToDefault={onChange}>
      <Checkbox
        className={s.configurationField__checkbox}
        checked={Boolean(value)}
        label={fieldName}
        onChange={handleChange}
        readOnly={isReadonly}
        onKeyDown={handleKeyDown}
      />
    </ConfigurationField>
  );
};

export default BooleanControl;

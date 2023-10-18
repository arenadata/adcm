import Checkbox from '@uikit/Checkbox/Checkbox';
import ConfigurationField from './ConfigurationField';
import { JSONPrimitive } from '@models/json';
import { SingleSchemaDefinition } from '@models/adcm';
import s from './ConfigurationField.module.scss';

export interface BooleanControlProps {
  fieldName: string;
  value: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (value: JSONPrimitive) => void;
}

const BooleanControl = ({ fieldName, fieldSchema, value, isReadonly, onChange }: BooleanControlProps) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.checked);
  };

  return (
    <ConfigurationField label={fieldName} fieldSchema={fieldSchema} isReadonly={isReadonly} onChange={onChange}>
      <Checkbox
        className={s.configurationField__checkbox}
        checked={Boolean(value)}
        label={fieldName}
        onChange={handleChange}
        readOnly={isReadonly}
      />
    </ConfigurationField>
  );
};

export default BooleanControl;

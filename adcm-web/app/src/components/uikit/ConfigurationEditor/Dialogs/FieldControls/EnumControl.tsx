import Select from '@uikit/Select/SingleSelect/Select/Select';
import ConfigurationField from './ConfigurationField';
import { JSONPrimitive } from '@models/json';
import { SingleSchemaDefinition } from '@models/adcm';
import { getEnumOptions } from './EnumControl.utils';

export interface EnumControlProps {
  fieldName: string;
  value: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (value: JSONPrimitive) => void;
}

const EnumControl = ({ fieldName, value, fieldSchema, isReadonly, onChange }: EnumControlProps) => {
  const options = getEnumOptions(fieldSchema);

  const handleSelectChange = (newValue: unknown) => {
    onChange(newValue as JSONPrimitive);
  };

  return (
    <ConfigurationField label={fieldName} fieldSchema={fieldSchema} disabled={isReadonly} onResetToDefault={onChange}>
      <Select
        value={value}
        onChange={handleSelectChange}
        options={options}
        isSearchable={false}
        placeholder="Please select value"
        disabled={isReadonly}
      />
    </ConfigurationField>
  );
};

export default EnumControl;

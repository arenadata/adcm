import Select from '@uikit/Select/SingleSelect/Select/Select';
import ConfigurationField from './ConfigurationField';
import type { JSONPrimitive } from '@models/json';
import type { SingleSchemaDefinition } from '@models/adcm';
import { getEnumOptions } from './EnumControl.utils';

export interface EnumControlProps {
  fieldName: string;
  value: JSONPrimitive;
  defaultValue: JSONPrimitive;
  fieldSchema: SingleSchemaDefinition;
  isReadonly: boolean;
  onChange: (value: JSONPrimitive) => void;
}

const EnumControl = ({ fieldName, value, fieldSchema, defaultValue, isReadonly, onChange }: EnumControlProps) => {
  const options = getEnumOptions(fieldSchema);

  const handleSelectChange = (newValue: unknown) => {
    onChange(newValue as JSONPrimitive);
  };

  return (
    <ConfigurationField
      label={fieldName}
      fieldSchema={fieldSchema}
      defaultValue={defaultValue}
      disabled={isReadonly}
      onResetToDefault={onChange}
    >
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

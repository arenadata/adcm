import { SingleSchemaDefinition } from '@models/adcm';
import { JSONPrimitive } from '@models/json';
import FormField from '@uikit/FormField/FormField';
import Button from '@uikit/Button/Button';
import s from './ConfigurationField.module.scss';

export interface ConfigurationFieldProps extends React.PropsWithChildren {
  label: string;
  error?: string;
  children: React.ReactElement<{ hasError?: boolean }>;
  fieldSchema: SingleSchemaDefinition;
  onChange: (value: JSONPrimitive) => void;
}

const ConfigurationField = ({ label, error, fieldSchema, children, onChange }: ConfigurationFieldProps) => {
  const handleRevertClick = () => {
    onChange((fieldSchema.default ?? '') as JSONPrimitive);
  };

  return (
    <div className={s.configurationField}>
      <FormField className={s.configurationField__control} label={label} error={error}>
        {children}
      </FormField>
      <div className={s.configurationField__actions}>
        <Button variant="secondary" iconLeft="g1-return" onClick={handleRevertClick} />
        <Button
          variant="secondary"
          iconLeft="marker-info"
          title={fieldSchema.description}
          tooltipProps={{ placement: 'bottom' }}
        />
      </div>
    </div>
  );
};

export default ConfigurationField;

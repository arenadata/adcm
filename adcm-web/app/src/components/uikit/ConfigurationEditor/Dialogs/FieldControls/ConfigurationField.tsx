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
  disabled: boolean;
  onResetToDefault: (value: JSONPrimitive) => void;
}

const ConfigurationField = ({
  label,
  error,
  fieldSchema,
  children,
  disabled,
  onResetToDefault,
}: ConfigurationFieldProps) => {
  const handleResetToDefaultClick = () => {
    onResetToDefault(fieldSchema.default as JSONPrimitive);
  };

  return (
    <div className={s.configurationField}>
      <FormField className={s.configurationField__control} label={label} error={error} hint={fieldSchema.description}>
        {children}
      </FormField>
      <div className={s.configurationField__actions}>
        <Button
          variant="tertiary"
          iconLeft="g1-return"
          disabled={disabled}
          title="Reset to default"
          tooltipProps={{ placement: 'bottom' }}
          onClick={handleResetToDefaultClick}
        />
      </div>
    </div>
  );
};

export default ConfigurationField;

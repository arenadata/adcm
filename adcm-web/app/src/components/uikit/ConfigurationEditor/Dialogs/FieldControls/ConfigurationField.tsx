import type { SchemaDefinition } from '@models/adcm';
import FormField from '@uikit/FormField/FormField';
import Button from '@uikit/Button/Button';
import s from './ConfigurationField.module.scss';

export interface ConfigurationFieldProps extends React.PropsWithChildren {
  label: string;
  error?: string;
  children: React.ReactElement<{ hasError?: boolean }>;
  fieldSchema: SchemaDefinition;
  disabled: boolean;
  onResetToDefault?: () => void;
}

const ConfigurationField = ({
  label,
  error,
  fieldSchema,
  children,
  disabled,
  onResetToDefault,
}: ConfigurationFieldProps) => (
  <div className={s.configurationField}>
    <FormField className={s.configurationField__control} label={label} error={error} hint={fieldSchema.description}>
      {children}
    </FormField>
    {onResetToDefault && (
      <div className={s.configurationField__actions}>
        <Button
          variant="tertiary"
          iconLeft="g1-return"
          disabled={disabled}
          title="Reset to default"
          tooltipProps={{ placement: 'bottom' }}
          onClick={onResetToDefault}
          tabIndex={-1}
        />
      </div>
    )}
  </div>
);

export default ConfigurationField;

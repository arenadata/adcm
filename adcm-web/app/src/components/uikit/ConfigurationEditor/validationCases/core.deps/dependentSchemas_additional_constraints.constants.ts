import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const dependentSchemas_additional_constraints_description =
  'deps: dependentSchemas. Если задан `role=admin`, то `adminCode` обязателен и должен быть длиной >= 4.';

export const dependentSchemas_additional_constraints_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core deps: dependentSchemas (constraints)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    role: { title: 'role', type: 'string', enum: ['user', 'admin'], readOnly: false },
    adminCode: { title: 'adminCode', type: 'string', minLength: 4, readOnly: false },
  },
  dependentSchemas: {
    role: {
      if: { properties: { role: { const: 'admin' } } },
      // biome-ignore lint/suspicious/noThenProperty: JSON Schema keyword `then`.
      then: { required: ['adminCode'] },
      else: {},
    },
  },
};

export const dependentSchemas_additional_constraints_datasets = {
  valid_user_without_adminCode: { role: 'user' },
  valid_admin_with_adminCode: { role: 'admin', adminCode: 'abcd' },
  invalid_admin_missing_adminCode: { role: 'admin' },
  invalid_adminCode_too_short: { role: 'admin', adminCode: 'a' },
} satisfies Record<string, ConfigurationData>;

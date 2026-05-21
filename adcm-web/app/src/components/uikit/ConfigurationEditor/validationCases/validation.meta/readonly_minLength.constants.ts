import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const readonly_minLength_description =
  'meta: readOnly не отключает JSON Schema — minLength по-прежнему даёт ошибку валидации.';

export const readonly_minLength_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation meta: readOnly + minLength',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    note: {
      title: 'note',
      type: 'string',
      minLength: 5,
      readOnly: true,
    },
  },
  required: ['note'],
};

export const readonly_minLength_datasets = {
  invalid_too_short: { note: 'ab' },
} satisfies Record<string, ConfigurationData>;

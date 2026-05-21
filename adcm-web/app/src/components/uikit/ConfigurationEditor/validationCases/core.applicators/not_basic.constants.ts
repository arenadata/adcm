import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const not_basic_description =
  'not: инвертирует результат подсхемы. Запрещаем значение 0 через not { const: 0 }.';

export const not_basic_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core applicators: not (basic)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Any integer except 0.',
      type: 'integer',
      readOnly: false,
      not: { const: 0 },
    },
  },
  required: ['value'],
};

export const not_basic_datasets = {
  valid_not_zero: { value: 1 },
  invalid_zero_is_forbidden: { value: 0 },
} satisfies Record<string, ConfigurationData>;

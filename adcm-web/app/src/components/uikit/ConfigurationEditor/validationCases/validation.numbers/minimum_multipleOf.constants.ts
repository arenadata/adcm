import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const minimum_multipleOf_description =
  'numbers: одновременно minimum и multipleOf (граница 10, шаг 5 → 10, 15, 20…).';

export const minimum_multipleOf_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation numbers: minimum + multipleOf',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      type: 'integer',
      minimum: 10,
      multipleOf: 5,
      readOnly: false,
    },
  },
  required: ['value'],
};

export const minimum_multipleOf_datasets = {
  valid_at_minimum: { value: 10 },
  valid_next_step: { value: 15 },
  invalid_below_minimum: { value: 5 },
  invalid_not_multiple_of_5: { value: 12 },
} satisfies Record<string, ConfigurationData>;

import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const ref_inside_allOf_description =
  'refs: $ref внутри allOf. Проверяем, что ограничения из $ref применяются, и ошибка подсвечивается на /value.';

export const ref_inside_allOf_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core refs: $ref inside allOf',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Must be integer >= 10 (via allOf[$ref]).',
      type: 'integer',
      readOnly: false,
      allOf: [{ $ref: '#/$defs/min10' }],
    },
  },
  required: ['value'],
  $defs: {
    min10: {
      type: 'integer',
      minimum: 10,
      readOnly: false,
    },
  },
};

export const ref_inside_allOf_datasets = {
  valid_minimum_10: { value: 10 },
  invalid_below_minimum_10: { value: 9 },
  invalid_missing_required_value: {},
} satisfies Record<string, ConfigurationData>;

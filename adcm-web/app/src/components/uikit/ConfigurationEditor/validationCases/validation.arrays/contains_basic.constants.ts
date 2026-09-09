import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const contains_basic_description = 'arrays: contains (basic). Массив должен содержать хотя бы один integer.';

export const contains_basic_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: contains (basic)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    arr: {
      title: 'arr',
      type: 'array',
      readOnly: false,
      items: {},
      contains: { type: 'integer' },
    },
  },
  required: ['arr'],
};

export const contains_basic_datasets = {
  valid_has_integer: { arr: [1] },
  invalid_empty_array: { arr: [] },
  invalid_no_integer: { arr: ['a', 'b'] },
} satisfies Record<string, ConfigurationData>;

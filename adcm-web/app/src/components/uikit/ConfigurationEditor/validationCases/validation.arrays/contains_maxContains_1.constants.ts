import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const contains_maxContains_1_description =
  'arrays: contains + maxContains=1. Массив должен содержать ровно один integer.';

export const contains_maxContains_1_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: contains + maxContains=1',
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
      maxContains: 1,
    },
  },
  required: ['arr'],
};

export const contains_maxContains_1_datasets = {
  valid_exactly_one_integer: { arr: [1, 'x'] },
  invalid_two_integers: { arr: [1, 2] },
  invalid_zero_integers: { arr: ['a'] },
} satisfies Record<string, ConfigurationData>;

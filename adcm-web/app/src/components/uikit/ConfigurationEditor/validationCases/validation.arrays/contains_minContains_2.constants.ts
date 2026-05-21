import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const contains_minContains_2_description =
  'arrays: contains + minContains=2. Массив должен содержать минимум два integer.';

export const contains_minContains_2_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: contains + minContains=2',
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
      minContains: 2,
    },
  },
  required: ['arr'],
};

export const contains_minContains_2_datasets = {
  valid_two_integers: { arr: [1, 2] },
  invalid_only_one_integer: { arr: [1, 'x'] },
  invalid_no_integers: { arr: ['a', 'b'] },
} satisfies Record<string, ConfigurationData>;

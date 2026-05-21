import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const uniqueItems_simple_description = 'arrays: uniqueItems. В массиве integer значения должны быть уникальны.';

export const uniqueItems_simple_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: uniqueItems',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    arr: {
      title: 'arr',
      type: 'array',
      readOnly: false,
      items: { type: 'integer' },
      uniqueItems: true,
    },
  },
  required: ['arr'],
};

export const uniqueItems_simple_datasets = {
  valid_unique: { arr: [1, 2, 3] },
  invalid_duplicates: { arr: [1, 1] },
} satisfies Record<string, ConfigurationData>;

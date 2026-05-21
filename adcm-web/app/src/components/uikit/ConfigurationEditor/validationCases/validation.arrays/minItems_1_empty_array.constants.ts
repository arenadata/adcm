import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const minItems_1_empty_array_description =
  'arrays: minItems: 1 при пустом массиве — отдельно от диапазона min/max в AR076.';

export const minItems_1_empty_array_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: minItems 1 vs empty array',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    arr: {
      title: 'arr',
      type: 'array',
      readOnly: false,
      items: { type: 'integer' },
      minItems: 1,
    },
  },
  required: ['arr'],
};

export const minItems_1_empty_array_datasets = {
  valid_one_item: { arr: [0] },
  invalid_empty: { arr: [] },
} satisfies Record<string, ConfigurationData>;

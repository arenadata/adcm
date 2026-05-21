import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const items_false_disallow_any_description =
  'arrays: items=false. Массив должен быть пустым (элементы запрещены).';

export const items_false_disallow_any_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: items=false',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    arr: {
      title: 'arr',
      type: 'array',
      readOnly: false,
      items: false,
    },
  },
  required: ['arr'],
};

export const items_false_disallow_any_datasets = {
  valid_empty_array: { arr: [] },
  invalid_has_item: { arr: [1] },
} satisfies Record<string, ConfigurationData>;

import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const prefixItems_items_after_prefix_description =
  'arrays: prefixItems + items. Первый элемент: integer. Начиная со второго — integer с minimum=10.';

export const prefixItems_items_after_prefix_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: items after prefixItems',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    arr: {
      title: 'arr',
      type: 'array',
      readOnly: false,
      prefixItems: [{ type: 'integer' }],
      items: { type: 'integer', minimum: 10 },
    },
  },
  required: ['arr'],
};

export const prefixItems_items_after_prefix_datasets = {
  valid_first_any_integer_then_min10: { arr: [0, 10, 11] },
  valid_single_item_only_prefix: { arr: [0] },
  invalid_second_below_10: { arr: [0, 9] },
} satisfies Record<string, ConfigurationData>;

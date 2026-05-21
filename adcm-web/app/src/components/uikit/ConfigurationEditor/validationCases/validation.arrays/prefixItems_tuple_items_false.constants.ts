import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const prefixItems_tuple_items_false_description =
  'arrays: prefixItems (tuple) + items=false. Ровно два элемента: string, затем integer. Дополнительные элементы запрещены.';

export const prefixItems_tuple_items_false_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: prefixItems tuple + items=false',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    arr: {
      title: 'arr',
      type: 'array',
      readOnly: false,
      prefixItems: [{ type: 'string' }, { type: 'integer' }],
      items: false,
    },
  },
  required: ['arr'],
};

export const prefixItems_tuple_items_false_datasets = {
  valid_two_items: { arr: ['x', 1] },
  invalid_extra_item: { arr: ['x', 1, true] },
  invalid_wrong_second_type: { arr: ['x', '1'] },
} satisfies Record<string, ConfigurationData>;

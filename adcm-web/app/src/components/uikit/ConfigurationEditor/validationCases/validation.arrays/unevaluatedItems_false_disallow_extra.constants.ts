import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const unevaluatedItems_false_disallow_extra_description =
  'arrays: unevaluatedItems=false. Элементы, которые не оцениваются prefixItems, запрещены.';

export const unevaluatedItems_false_disallow_extra_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: unevaluatedItems=false',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    arr: {
      title: 'arr',
      type: 'array',
      readOnly: false,
      prefixItems: [{ type: 'integer' }],
      // Without `items`, items after prefixItems stay unevaluated.
      unevaluatedItems: false,
    },
  },
  required: ['arr'],
};

export const unevaluatedItems_false_disallow_extra_datasets = {
  valid_only_prefix: { arr: [1] },
  invalid_has_extra_item: { arr: [1, 'x'] },
} satisfies Record<string, ConfigurationData>;

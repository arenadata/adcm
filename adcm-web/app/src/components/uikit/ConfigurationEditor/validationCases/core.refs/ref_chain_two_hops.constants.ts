import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const ref_chain_two_hops_description =
  'refs: $ref → $ref (цепочка). Свойство ссылается на $defs/A, который сам ссылается на $defs/B. Проверяем корректность разыменования по цепочке и подсветку по /value.';

export const ref_chain_two_hops_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core refs: $ref chain (two hops)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Must be integer >= 10. Schema is reached by $ref → $ref.',
      $ref: '#/$defs/A',
      type: 'integer',
      readOnly: false,
    },
  },
  required: ['value'],
  $defs: {
    A: {
      $ref: '#/$defs/B',
      readOnly: false,
    },
    B: {
      type: 'integer',
      minimum: 10,
      readOnly: false,
    },
  },
};

export const ref_chain_two_hops_datasets = {
  valid_minimum_10: { value: 10 },
  invalid_below_minimum_10: { value: 9 },
  invalid_missing_required_value: {},
} satisfies Record<string, ConfigurationData>;

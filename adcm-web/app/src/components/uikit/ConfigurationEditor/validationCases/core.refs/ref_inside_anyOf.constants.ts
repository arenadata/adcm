import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const ref_inside_anyOf_description =
  'refs: $ref внутри anyOf. Проверяем, что проходит, если валидна хотя бы одна ветка, и падает если ни одна не валидна. Подсветка на /value.';

export const ref_inside_anyOf_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core refs: $ref inside anyOf',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Must be integer <= 0 OR integer >= 10 (anyOf with $ref branches).',
      type: 'integer',
      readOnly: false,
      anyOf: [{ $ref: '#/$defs/le0' }, { $ref: '#/$defs/ge10' }],
    },
  },
  required: ['value'],
  $defs: {
    le0: {
      type: 'integer',
      maximum: 0,
      readOnly: false,
    },
    ge10: {
      type: 'integer',
      minimum: 10,
      readOnly: false,
    },
  },
};

export const ref_inside_anyOf_datasets = {
  valid_branch_le0: { value: 0 },
  valid_branch_ge10: { value: 10 },
  invalid_between_1_and_9: { value: 5 },
} satisfies Record<string, ConfigurationData>;

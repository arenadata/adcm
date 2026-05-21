import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const ref_inside_oneOf_description =
  'refs: $ref внутри oneOf. Проверяем: ровно одна ветка должна быть валидна. Кейсы: 0 веток (fail), 2 ветки (fail). Подсветка на /value.';

export const ref_inside_oneOf_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core refs: $ref inside oneOf',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Exactly one of two overlapping ranges (oneOf with $ref branches): [0..10] vs [5..15].',
      type: 'integer',
      readOnly: false,
      oneOf: [{ $ref: '#/$defs/rangeA' }, { $ref: '#/$defs/rangeB' }],
    },
  },
  required: ['value'],
  $defs: {
    rangeA: {
      type: 'integer',
      minimum: 0,
      maximum: 10,
      readOnly: false,
    },
    rangeB: {
      type: 'integer',
      minimum: 5,
      maximum: 15,
      readOnly: false,
    },
  },
};

export const ref_inside_oneOf_datasets = {
  valid_exactly_one_branch_rangeA_only: { value: 2 }, // in [0..10], not in [5..15]
  valid_exactly_one_branch_rangeB_only: { value: 12 }, // in [5..15], not in [0..10]
  invalid_zero_branches_outside_both_ranges: { value: -1 }, // in neither
  invalid_two_branches_valid_overlap: { value: 7 }, // in both [0..10] and [5..15]
} satisfies Record<string, ConfigurationData>;

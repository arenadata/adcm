import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const oneOf_basic_description =
  'oneOf: значение валидно, если проходит ровно одну ветку. Проверяем 1 ветка валидна, 0 веток валидно, 2 ветки валидно (overlap).';

export const oneOf_basic_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core applicators: oneOf (basic)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Exactly one of two overlapping ranges: [0..10] vs [5..15].',
      type: 'integer',
      readOnly: false,
      oneOf: [
        { type: 'integer', minimum: 0, maximum: 10 },
        { type: 'integer', minimum: 5, maximum: 15 },
      ],
    },
  },
  required: ['value'],
};

export const oneOf_basic_datasets = {
  valid_first_only: { value: 2 },
  valid_second_only: { value: 12 },
  invalid_zero_branches: { value: -1 },
  invalid_two_branches_overlap: { value: 7 },
} satisfies Record<string, ConfigurationData>;

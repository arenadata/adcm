import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const anyOf_basic_description =
  'anyOf: значение валидно, если проходит хотя бы одну ветку. Проверяем 1 ветка валидна и 0 веток валидно.';

export const anyOf_basic_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core applicators: anyOf (basic)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Must be integer <= 0 OR integer >= 10.',
      type: 'integer',
      readOnly: false,
      anyOf: [{ maximum: 0 }, { minimum: 10 }],
    },
  },
  required: ['value'],
};

export const anyOf_basic_datasets = {
  valid_first_branch: { value: 0 },
  valid_second_branch: { value: 10 },
  invalid_no_branches: { value: 5 },
} satisfies Record<string, ConfigurationData>;

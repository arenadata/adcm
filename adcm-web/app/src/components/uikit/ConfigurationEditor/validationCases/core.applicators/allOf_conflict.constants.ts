import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const allOf_conflict_description =
  'allOf conflict: ветки противоречат (minimum > maximum). Ожидаем, что любое значение будет невалидно, подсветка на /value.';

export const allOf_conflict_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core applicators: allOf (conflict)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'All values should fail due to conflicting allOf constraints.',
      type: 'integer',
      readOnly: false,
      allOf: [{ minimum: 10 }, { maximum: 0 }],
    },
  },
  required: ['value'],
};

export const allOf_conflict_datasets = {
  invalid_any_value_fails: { value: 5 },
} satisfies Record<string, ConfigurationData>;

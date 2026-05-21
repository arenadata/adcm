import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const anyOf_multiple_valid_description =
  'anyOf multiple valid: две ветки одновременно валидны — для anyOf это OK. Проверяем, что значение проходит.';

export const anyOf_multiple_valid_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core applicators: anyOf (multiple valid branches)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Value 7 matches both branches (>=0 and <=10). anyOf should pass.',
      type: 'integer',
      readOnly: false,
      anyOf: [{ minimum: 0 }, { maximum: 10 }],
    },
  },
  required: ['value'],
};

export const anyOf_multiple_valid_datasets = {
  valid_both_branches_match: { value: 7 },
} satisfies Record<string, ConfigurationData>;

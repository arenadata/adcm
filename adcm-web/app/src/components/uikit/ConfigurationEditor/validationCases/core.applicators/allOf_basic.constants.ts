import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const allOf_basic_description =
  'allOf: значение должно одновременно удовлетворять всем веткам. Проверяем валидный кейс и кейс, где одна ветка ломается (minimum).';

export const allOf_basic_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core applicators: allOf (basic)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Must be integer between 0 and 10 (inclusive) due to allOf.',
      type: 'integer',
      readOnly: false,
      allOf: [{ minimum: 0 }, { maximum: 10 }],
    },
  },
  required: ['value'],
};

export const allOf_basic_datasets = {
  valid_in_range: { value: 5 },
  invalid_below_minimum: { value: -1 },
  invalid_above_maximum: { value: 11 },
} satisfies Record<string, ConfigurationData>;

import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const minimum_maximum_description = 'numbers: integer с minimum и maximum (включительно).';

export const minimum_maximum_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation numbers: minimum + maximum',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      type: 'integer',
      minimum: 0,
      maximum: 100,
      readOnly: false,
    },
  },
  required: ['value'],
};

export const minimum_maximum_datasets = {
  valid_mid_range: { value: 50 },
  invalid_below_minimum: { value: -1 },
  invalid_above_maximum: { value: 101 },
} satisfies Record<string, ConfigurationData>;

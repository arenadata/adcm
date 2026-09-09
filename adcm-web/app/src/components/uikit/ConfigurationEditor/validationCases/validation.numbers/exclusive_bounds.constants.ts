import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const exclusive_bounds_description =
  'numbers: number с exclusiveMinimum и exclusiveMaximum (2020-12: числовые границы).';

export const exclusive_bounds_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation numbers: exclusiveMinimum + exclusiveMaximum',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      type: 'number',
      exclusiveMinimum: 0,
      exclusiveMaximum: 10,
      readOnly: false,
    },
  },
  required: ['value'],
};

export const exclusive_bounds_datasets = {
  valid_between_open_bounds: { value: 5 },
  invalid_equal_to_exclusiveMinimum: { value: 0 },
  invalid_equal_to_exclusiveMaximum: { value: 10 },
} satisfies Record<string, ConfigurationData>;

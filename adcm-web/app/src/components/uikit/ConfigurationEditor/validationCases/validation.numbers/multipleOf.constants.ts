import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const multipleOf_description = 'numbers: integer с multipleOf (кратность).';

export const multipleOf_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation numbers: multipleOf',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      type: 'integer',
      multipleOf: 5,
      readOnly: false,
    },
  },
  required: ['value'],
};

export const multipleOf_datasets = {
  valid_multiple_of_5: { value: 15 },
  invalid_not_multiple_of_5: { value: 12 },
} satisfies Record<string, ConfigurationData>;

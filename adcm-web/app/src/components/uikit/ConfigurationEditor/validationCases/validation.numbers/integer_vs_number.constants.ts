import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const integer_vs_number_description =
  'numbers: рядом integer и number — дробь недопустима для integer, допустима для number.';

export const integer_vs_number_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation numbers: integer vs number',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    i: {
      title: 'i',
      type: 'integer',
      readOnly: false,
    },
    n: {
      title: 'n',
      type: 'number',
      readOnly: false,
    },
  },
  required: ['i', 'n'],
};

export const integer_vs_number_datasets = {
  valid: { i: 1, n: 1.5 },
  invalid_integer_fraction: { i: 1.2, n: 1.5 },
} satisfies Record<string, ConfigurationData>;

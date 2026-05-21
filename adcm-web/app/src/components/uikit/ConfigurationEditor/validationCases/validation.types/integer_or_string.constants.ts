import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const integer_or_string_description =
  'types: type: ["integer", "string"] — целое или строка (объединение примитивов).';

export const integer_or_string_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation types: integer | string',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      type: ['integer', 'string'],
      readOnly: false,
    },
  },
  required: ['value'],
};

export const integer_or_string_datasets = {
  valid_integer: { value: 7 },
  valid_string: { value: 'seven' },
  invalid_boolean: { value: true },
} satisfies Record<string, ConfigurationData>;

import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const oneOf_many_variants_description =
  'discriminator: discriminator + oneOf из 4 веток (string/number/object/array). Ветка выбирается по _selection, можно вручную переключать.';

export const oneOf_many_variants_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: oneOf (many variants) + discriminator',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    variant: {
      title: 'variant',
      type: 'object',
      readOnly: false,
      discriminator: { propertyName: '_selection' },
      oneOf: [
        {
          type: 'object',
          additionalProperties: false,
          required: ['_selection', 'value'],
          properties: {
            _selection: { const: 'string', title: '_selection' },
            value: { title: 'value', type: 'string', minLength: 3 },
          },
        },
        {
          type: 'object',
          additionalProperties: false,
          required: ['_selection', 'value'],
          properties: {
            _selection: { const: 'number', title: '_selection' },
            value: { title: 'value', type: 'number', minimum: 10 },
          },
        },
        {
          type: 'object',
          additionalProperties: false,
          required: ['_selection', 'value'],
          properties: {
            _selection: { const: 'object', title: '_selection' },
            value: {
              title: 'value',
              type: 'object',
              additionalProperties: false,
              required: ['name'],
              properties: { name: { type: 'string', minLength: 1 } },
            },
          },
        },
        {
          type: 'object',
          additionalProperties: false,
          required: ['_selection', 'value'],
          properties: {
            _selection: { const: 'array', title: '_selection' },
            value: { title: 'value', type: 'array', items: { type: 'integer' }, minItems: 2 },
          },
        },
      ],
    },
  },
  required: ['variant'],
};

export const oneOf_many_variants_datasets = {
  valid_string: { variant: { _selection: 'string', value: 'abc' } },
  valid_number: { variant: { _selection: 'number', value: 10 } },
  valid_object: { variant: { _selection: 'object', value: { name: 'x' } } },
  valid_array: { variant: { _selection: 'array', value: [1, 2] } },
  invalid_matches_none: { variant: { _selection: 'unknown', value: true } },
  invalid_string_too_short: { variant: { _selection: 'string', value: 'a' } },
  invalid_array_too_short: { variant: { _selection: 'array', value: [1] } },
} satisfies Record<string, ConfigurationData>;

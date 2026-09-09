import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const oneOf_nullable_array_description =
  'discriminator: discriminator + oneOf: [array, null]. Ветка выбирается по _selection; внутри ветки поле list nullable через oneOf.';

export const oneOf_nullable_array_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: oneOf (nullable array) + discriminator',
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
          required: ['_selection', 'list'],
          properties: {
            _selection: { const: 'list', title: '_selection' },
            list: {
              title: 'list',
              oneOf: [{ type: 'array', items: { type: 'integer' }, minItems: 1 }, { type: 'null' }],
            },
          },
        },
      ],
    },
  },
  required: ['variant'],
};

export const oneOf_nullable_array_datasets = {
  valid_null: { variant: { _selection: 'list', list: null } },
  valid_array: { variant: { _selection: 'list', list: [1, 2, 3] } },
  invalid_empty_array: { variant: { _selection: 'list', list: [] } },
  invalid_wrong_item_type: { variant: { _selection: 'list', list: [1, 'x'] } },
} satisfies Record<string, ConfigurationData>;

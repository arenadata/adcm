import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const null_only_description = 'types: поле только с type: "null" — допустимо только JSON null.';

export const null_only_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation types: null only',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    empty: {
      title: 'empty',
      type: 'null',
      readOnly: false,
    },
  },
  required: ['empty'],
};

export const null_only_datasets = {
  valid_null: { empty: null },
  invalid_string: { empty: 'not null' },
} satisfies Record<string, ConfigurationData>;

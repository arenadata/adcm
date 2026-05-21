import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const string_or_null_description = 'types: поле с type: ["string", "null"] — допустимы строка или null.';

export const string_or_null_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation types: string | null',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    label: {
      title: 'label',
      type: ['string', 'null'],
      readOnly: false,
    },
  },
  required: ['label'],
};

export const string_or_null_datasets = {
  valid_string: { label: 'text' },
  valid_null: { label: null },
  invalid_number: { label: 42 },
} satisfies Record<string, ConfigurationData>;

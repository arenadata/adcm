import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const type_boolean_description = 'boolean: type: "boolean" — только true/false.';

export const type_boolean_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation booleans: type boolean',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    enabled: {
      title: 'enabled',
      type: 'boolean',
      readOnly: false,
    },
  },
  required: ['enabled'],
};

export const type_boolean_datasets = {
  valid_true: { enabled: true },
  valid_false: { enabled: false },
  invalid_string: { enabled: 'yes' },
} satisfies Record<string, ConfigurationData>;

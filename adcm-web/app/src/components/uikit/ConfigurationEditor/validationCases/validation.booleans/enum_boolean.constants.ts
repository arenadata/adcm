import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const enum_boolean_description = 'boolean: enum из двух булевых значений [true, false].';

export const enum_boolean_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation booleans: enum [true, false]',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    state: {
      title: 'state',
      type: 'boolean',
      enum: [true, false],
      readOnly: false,
    },
  },
  required: ['state'],
};

export const enum_boolean_datasets = {
  valid_true: { state: true },
  valid_false: { state: false },
  invalid_number: { state: 1 },
} satisfies Record<string, ConfigurationData>;

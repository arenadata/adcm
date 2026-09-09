import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const const_true_description = 'boolean: поле boolean с const: true — только значение true.';

export const const_true_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation booleans: const true',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    flag: {
      title: 'flag',
      type: 'boolean',
      const: true,
      readOnly: false,
    },
  },
  required: ['flag'],
};

export const const_true_datasets = {
  valid_true: { flag: true },
  invalid_false: { flag: false },
} satisfies Record<string, ConfigurationData>;

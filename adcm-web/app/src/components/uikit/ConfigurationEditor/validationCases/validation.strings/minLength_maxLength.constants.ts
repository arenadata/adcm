import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const minLength_maxLength_description = 'strings: string с minLength и maxLength.';

export const minLength_maxLength_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation strings: minLength + maxLength',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    label: {
      title: 'label',
      type: 'string',
      minLength: 2,
      maxLength: 8,
      readOnly: false,
    },
  },
  required: ['label'],
};

export const minLength_maxLength_datasets = {
  valid_length_in_range: { label: 'abc' },
  invalid_too_short: { label: 'a' },
  invalid_too_long: { label: '123456789' },
} satisfies Record<string, ConfigurationData>;

import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const minItems_maxItems_description = 'arrays: minItems/maxItems. Длина массива должна быть от 2 до 3.';

export const minItems_maxItems_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: minItems/maxItems',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    arr: {
      title: 'arr',
      type: 'array',
      readOnly: false,
      items: { type: 'integer' },
      minItems: 2,
      maxItems: 3,
    },
  },
  required: ['arr'],
};

export const minItems_maxItems_datasets = {
  valid_length_2: { arr: [1, 2] },
  valid_length_3: { arr: [1, 2, 3] },
  invalid_too_short: { arr: [1] },
  invalid_too_long: { arr: [1, 2, 3, 4] },
} satisfies Record<string, ConfigurationData>;

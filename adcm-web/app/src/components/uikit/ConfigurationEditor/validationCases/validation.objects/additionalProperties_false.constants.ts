import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const additionalProperties_false_description = 'objects: additionalProperties: false — лишние ключи запрещены.';

export const additionalProperties_false_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation objects: additionalProperties false',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    name: { title: 'name', type: 'string', readOnly: false },
  },
  required: ['name'],
};

export const additionalProperties_false_datasets = {
  valid_only_declared: { name: 'ok' },
  invalid_extra_key: { name: 'ok', surprise: 'no' },
} satisfies Record<string, ConfigurationData>;

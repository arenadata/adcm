import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const patternProperties_description =
  'objects: patternProperties — свойства, ключи которых совпадают с шаблоном, валидируются по своей схеме.';

export const patternProperties_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation objects: patternProperties',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {},
  patternProperties: {
    '^[a-z]+$': {
      title: 'lowerKey',
      type: 'string',
      readOnly: false,
    },
  },
};

export const patternProperties_datasets = {
  valid_matching_keys: { ab: 'v1', cd: 'v2' },
  invalid_key_breaks_pattern: { Ab: 'x' },
  invalid_value_type: { ab: 1 },
} satisfies Record<string, ConfigurationData>;

import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const propertyNames_description =
  'objects: propertyNames — все имена свойств должны удовлетворять вложенной схеме (здесь pattern).';

export const propertyNames_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation objects: propertyNames',
  type: 'object',
  readOnly: false,
  additionalProperties: true,
  properties: {},
  propertyNames: {
    pattern: '^[a-z]{3,}$',
  },
};

export const propertyNames_datasets = {
  valid_keys_ok: { abc: 1, defghi: 2 },
  invalid_key_too_short: { ab: 1 },
  invalid_key_uppercase: { Abc: 1 },
} satisfies Record<string, ConfigurationData>;

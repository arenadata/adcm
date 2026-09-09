import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const enum_const_description = 'strings: string с enum и полем с const.';

export const enum_const_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation strings: enum + const',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    tier: {
      title: 'tier',
      type: 'string',
      enum: ['small', 'medium', 'large'],
      readOnly: false,
    },
    version: {
      title: 'version',
      type: 'string',
      const: '1.0',
      readOnly: false,
    },
  },
  required: ['tier', 'version'],
};

export const enum_const_datasets = {
  valid_both_ok: { tier: 'medium', version: '1.0' },
  invalid_tier_not_in_enum: { tier: 'huge', version: '1.0' },
  invalid_version_not_const: { tier: 'small', version: '2.0' },
} satisfies Record<string, ConfigurationData>;

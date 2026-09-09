import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const pattern_description = 'strings: string с pattern (регулярное выражение ECMA-262).';

export const pattern_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation strings: pattern',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    code: {
      title: 'code',
      type: 'string',
      pattern: '^[A-Z]{3}-[0-9]{4}$',
      readOnly: false,
    },
  },
  required: ['code'],
};

export const pattern_datasets = {
  valid_matches_pattern: { code: 'ABC-1234' },
  invalid_no_match: { code: 'abc-1234' },
} satisfies Record<string, ConfigurationData>;

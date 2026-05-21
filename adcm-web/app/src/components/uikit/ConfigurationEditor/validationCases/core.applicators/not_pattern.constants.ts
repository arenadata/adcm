import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const not_pattern_description =
  'not + pattern: запрещаем строки, которые матчятся на ^admin.* (например "admin", "administrator"). Проверяем pass/fail.';

export const not_pattern_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core applicators: not (pattern)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Any string except those starting with "admin".',
      type: 'string',
      readOnly: false,
      not: { type: 'string', pattern: '^admin.*' },
    },
  },
  required: ['value'],
};

export const not_pattern_datasets = {
  valid_user: { value: 'user' },
  invalid_admin_forbidden: { value: 'admin' },
  invalid_administrator_forbidden: { value: 'administrator' },
} satisfies Record<string, ConfigurationData>;

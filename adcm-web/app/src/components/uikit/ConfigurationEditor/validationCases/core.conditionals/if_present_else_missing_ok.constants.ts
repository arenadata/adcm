import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const if_present_else_missing_ok_description =
  'if присутствует, else отсутствует: else должен игнорироваться. Валидность не должна меняться.';

export const if_present_else_missing_ok_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core conditionals: if present, else missing (ok)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    flag: { title: 'flag', type: 'boolean', readOnly: false },
  },
  if: { properties: { flag: { const: true } } },
  // biome-ignore lint/suspicious/noThenProperty: JSON Schema keyword `then`.
  then: {},
  // No `else`
};

export const if_present_else_missing_ok_datasets = {
  valid_flag_true: { flag: true },
  valid_flag_false: { flag: false },
  valid_flag_missing: {},
} satisfies Record<string, ConfigurationData>;

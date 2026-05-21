import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const if_then_else_basic_description =
  'if/then/else (basic): если mode="a" → required aValue, иначе → required bValue. Проверяем обе ветки и ошибки required на /aValue или /bValue.';

export const if_then_else_basic_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core conditionals: if/then/else (basic)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    mode: { title: 'mode', type: 'string', readOnly: false },
    aValue: { title: 'aValue', type: 'string', readOnly: false },
    bValue: { title: 'bValue', type: 'string', readOnly: false },
  },
  required: ['mode'],
  if: {
    properties: { mode: { const: 'a' } },
    required: ['mode'],
  },
  // biome-ignore lint/suspicious/noThenProperty: JSON Schema keyword `then`.
  then: { required: ['aValue'] },
  else: { required: ['bValue'] },
};

export const if_then_else_basic_datasets = {
  valid_then_branch: { mode: 'a', aValue: 'ok' },
  invalid_then_branch_missing_aValue: { mode: 'a' },
  valid_else_branch: { mode: 'b', bValue: 'ok' },
  invalid_else_branch_missing_bValue: { mode: 'b' },
} satisfies Record<string, ConfigurationData>;

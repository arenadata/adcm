import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const if_then_basic_description =
  'if/then (basic): если mode="a", то требуется поле aValue. Проверяем валидный и невалидный кейс для then-ветки.';

export const if_then_basic_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core conditionals: if/then (basic)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    mode: { title: 'mode', type: 'string', readOnly: false },
    aValue: { title: 'aValue', type: 'string', readOnly: false },
  },
  required: ['mode'],
  if: {
    properties: { mode: { const: 'a' } },
    required: ['mode'],
  },
  // biome-ignore lint/suspicious/noThenProperty: JSON Schema keyword `then`.
  then: {
    required: ['aValue'],
  },
};

export const if_then_basic_datasets = {
  valid_then_taken: { mode: 'a', aValue: 'ok' },
  invalid_then_taken_missing_required: { mode: 'a' },
  valid_if_false_then_ignored: { mode: 'b' },
} satisfies Record<string, ConfigurationData>;

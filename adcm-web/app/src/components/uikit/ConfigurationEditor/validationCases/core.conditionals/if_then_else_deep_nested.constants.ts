import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const if_then_else_deep_nested_description =
  'if/then/else (deep): ветвление по mode влияет на required во вложенном объекте config.*. Проверяем корректные instancePath (/config/aValue или /config/bValue).';

export const if_then_else_deep_nested_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core conditionals: if/then/else (deep nested)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    mode: { title: 'mode', type: 'string', readOnly: false },
    config: {
      title: 'config',
      type: 'object',
      readOnly: false,
      additionalProperties: false,
      properties: {
        aValue: { title: 'aValue', type: 'string', readOnly: false },
        bValue: { title: 'bValue', type: 'string', readOnly: false },
      },
      required: [],
    },
  },
  required: ['mode', 'config'],
  if: {
    properties: { mode: { const: 'a' } },
    required: ['mode'],
  },
  // biome-ignore lint/suspicious/noThenProperty: JSON Schema keyword `then`.
  then: {
    properties: {
      config: { required: ['aValue'] },
    },
  },
  else: {
    properties: {
      config: { required: ['bValue'] },
    },
  },
};

export const if_then_else_deep_nested_datasets = {
  valid_then_nested: { mode: 'a', config: { aValue: 'ok' } },
  invalid_then_nested_missing: { mode: 'a', config: {} },
  valid_else_nested: { mode: 'b', config: { bValue: 'ok' } },
  invalid_else_nested_missing: { mode: 'b', config: {} },
} satisfies Record<string, ConfigurationData>;

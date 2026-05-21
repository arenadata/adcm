import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const mixed_props_pattern_unevaluated_description =
  'objects: одновременно properties, patternProperties и unevaluatedProperties: false — регресс дерева и путей ошибок.';

export const mixed_props_pattern_unevaluated_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation objects: properties + patternProperties + unevaluatedProperties',
  type: 'object',
  readOnly: false,
  properties: {
    name: { title: 'name', type: 'string', readOnly: false },
  },
  patternProperties: {
    '^meta_': {
      title: 'meta_prefixed',
      type: 'boolean',
      readOnly: false,
    },
  },
  unevaluatedProperties: false,
};

export const mixed_props_pattern_unevaluated_datasets = {
  valid_declared_and_pattern: { name: 'app', meta_ready: true },
  invalid_stray_key: { name: 'app', meta_ready: true, extra: 1 },
} satisfies Record<string, ConfigurationData>;

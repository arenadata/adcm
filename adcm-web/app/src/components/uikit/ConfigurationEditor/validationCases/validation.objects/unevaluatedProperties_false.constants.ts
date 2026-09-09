import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const unevaluatedProperties_false_description =
  'objects: unevaluatedProperties: false — любые свойства вне properties и не покрытые patternProperties считаются лишними.';

export const unevaluatedProperties_false_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation objects: unevaluatedProperties false',
  type: 'object',
  readOnly: false,
  properties: {
    id: { title: 'id', type: 'string', readOnly: false },
  },
  patternProperties: {
    '^x_': {
      title: 'x_prefixed',
      type: 'integer',
      readOnly: false,
    },
  },
  unevaluatedProperties: false,
};

export const unevaluatedProperties_false_datasets = {
  valid_covered_only: { id: 'main', x_count: 0 },
  invalid_stray_property: { id: 'main', other: 1 },
} satisfies Record<string, ConfigurationData>;

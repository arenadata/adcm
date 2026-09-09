import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const ref_missing_pointer_description =
  'refs: битый $ref (missing pointer). Ссылка указывает на несуществующий $defs. Проверяем, что UI не падает и показывает ошибку схемы на корне.';

export const ref_missing_pointer_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core refs: broken $ref (missing pointer)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Schema compilation should fail due to unresolved $ref.',
      $ref: '#/$defs/doesNotExist',
      type: 'integer',
      readOnly: false,
    },
  },
  required: ['value'],
  $defs: {
    // Intentionally empty: target does not exist.
  },
};

export const ref_missing_pointer_datasets = {
  any_value_still_schema_error: { value: 1 },
  missing_required_value_also_schema_error: {},
} satisfies Record<string, ConfigurationData>;

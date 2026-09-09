import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const defs_ref_simple_description =
  'refs: $defs + $ref. Поле ссылается на тип из $defs. Проверяем базовую работоспособность refs и подсветку ошибок на конкретном поле.';

export const defs_ref_simple_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core refs: $defs + $ref (positive integer)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Must be a positive integer (> 0).',
      $ref: '#/$defs/positiveInteger',
      // ConfigurationEditor UI does not dereference `$ref` when choosing control,
      // so we provide `type` locally to keep the field editable.
      type: 'integer',
      readOnly: false,
    },
  },
  required: ['value'],
  $defs: {
    positiveInteger: {
      type: 'integer',
      exclusiveMinimum: 0,
      readOnly: false,
    },
  },
};

export const defs_ref_simple_datasets = {
  valid_positive_1: { value: 1 },
  invalid_zero_fails_exclusiveMinimum: { value: 0 },
  invalid_missing_required_value: {},
} satisfies Record<string, ConfigurationData>;

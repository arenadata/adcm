import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const enum_const_description =
  'numbers: integer с enum и отдельным полем с const (ограничение одного значения).';

export const enum_const_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation numbers: enum + const',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    mode: {
      title: 'mode',
      type: 'integer',
      enum: [1, 2, 3],
      readOnly: false,
    },
    fixed: {
      title: 'fixed',
      type: 'integer',
      const: 42,
      readOnly: false,
    },
  },
  required: ['mode', 'fixed'],
};

export const enum_const_datasets = {
  valid_both_ok: { mode: 2, fixed: 42 },
  invalid_mode_not_in_enum: { mode: 9, fixed: 42 },
  invalid_fixed_not_const: { mode: 1, fixed: 0 },
} satisfies Record<string, ConfigurationData>;

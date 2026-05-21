import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const dependentSchemas_schema_branching_description =
  'deps: dependentSchemas меняет форму объекта. Если задан `mode=strict`, то требуется `threshold` (integer >= 10).';

export const dependentSchemas_schema_branching_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core deps: dependentSchemas (branching)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    mode: { title: 'mode', type: 'string', enum: ['lenient', 'strict'], readOnly: false },
    threshold: { title: 'threshold', type: 'integer', minimum: 10, readOnly: false },
  },
  dependentSchemas: {
    mode: {
      if: { properties: { mode: { const: 'strict' } } },
      // biome-ignore lint/suspicious/noThenProperty: JSON Schema keyword `then`.
      then: { required: ['threshold'] },
      else: {},
    },
  },
};

export const dependentSchemas_schema_branching_datasets = {
  valid_lenient_without_threshold: { mode: 'lenient' },
  valid_strict_with_threshold_10: { mode: 'strict', threshold: 10 },
  invalid_strict_missing_threshold: { mode: 'strict' },
  invalid_strict_threshold_below_10: { mode: 'strict', threshold: 9 },
} satisfies Record<string, ConfigurationData>;

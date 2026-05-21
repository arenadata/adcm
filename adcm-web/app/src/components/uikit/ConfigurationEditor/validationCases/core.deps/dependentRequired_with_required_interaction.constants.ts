import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const dependentRequired_with_required_interaction_description =
  'deps: dependentRequired + required. `enabled` обязателен всегда; если `enabled=true`, то обязателен `details`.';

export const dependentRequired_with_required_interaction_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core deps: dependentRequired + required (interaction)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    enabled: { title: 'enabled', type: 'boolean', readOnly: false },
    details: { title: 'details', type: 'string', readOnly: false },
  },
  required: ['enabled'],
  dependentSchemas: {
    enabled: {
      if: { properties: { enabled: { const: true } } },
      // biome-ignore lint/suspicious/noThenProperty: JSON Schema keyword `then`.
      then: { required: ['details'] },
      else: {},
    },
  },
};

export const dependentRequired_with_required_interaction_datasets = {
  valid_enabled_true_with_details: { enabled: true, details: 'ok' },
  valid_enabled_false_with_details: { enabled: false, details: 'ok' },
  invalid_missing_enabled: {},
  invalid_enabled_true_missing_details: { enabled: true },
} satisfies Record<string, ConfigurationData>;

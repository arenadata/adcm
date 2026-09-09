import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const oneOf_type_variants_description =
  'oneOf type variants: ветки различаются типом (string vs null). Проверяем, что string проходит по одной ветке, null — по другой, а number — 0 веток.';

export const oneOf_type_variants_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core applicators: oneOf (type variants)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description: 'Exactly one of: string OR null.',
      readOnly: false,
      // Keep this as a pure oneOf type variant case (no adjacent `type`),
      // otherwise `null` becomes invalid due to sibling keywords.
      oneOf: [{ type: 'null' }, { type: 'string' }],
    },
  },
  required: ['value'],
};

export const oneOf_type_variants_datasets = {
  valid_string_branch: { value: 'abc' },
  // Note: ConfigurationEditor stores `null` as clear value; this dataset checks oneOf null branch.
  valid_null_branch: { value: null },
  invalid_zero_branches_number: { value: 1 },
} satisfies Record<string, ConfigurationData>;

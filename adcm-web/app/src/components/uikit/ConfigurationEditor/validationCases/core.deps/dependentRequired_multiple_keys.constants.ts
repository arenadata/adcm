import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const dependentRequired_multiple_keys_description =
  'deps: dependentRequired с несколькими зависимостями. Для `a` нужно `b` и `c`.';

export const dependentRequired_multiple_keys_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core deps: dependentRequired (multiple)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    a: { title: 'a', type: 'string', readOnly: false },
    b: { title: 'b', type: 'string', readOnly: false },
    c: { title: 'c', type: 'string', readOnly: false },
  },
  dependentRequired: {
    a: ['b', 'c'],
  },
};

export const dependentRequired_multiple_keys_datasets = {
  valid_a_with_b_and_c: { a: 'x', b: 'y', c: 'z' },
  invalid_a_missing_b: { a: 'x', c: 'z' },
  invalid_a_missing_c: { a: 'x', b: 'y' },
} satisfies Record<string, ConfigurationData>;

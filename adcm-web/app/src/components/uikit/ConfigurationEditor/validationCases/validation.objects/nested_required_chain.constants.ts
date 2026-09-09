import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const nested_required_chain_description =
  'objects: цепочка required на трёх уровнях вложенности (корень → level1 → level2 → leaf).';

export const nested_required_chain_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation objects: nested required chain',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    level1: {
      title: 'level1',
      type: 'object',
      readOnly: false,
      additionalProperties: false,
      properties: {
        level2: {
          title: 'level2',
          type: 'object',
          readOnly: false,
          additionalProperties: false,
          properties: {
            leaf: { title: 'leaf', type: 'string', readOnly: false },
          },
          required: ['leaf'],
        },
      },
      required: ['level2'],
    },
  },
  required: ['level1'],
};

export const nested_required_chain_datasets = {
  valid_all_present: { level1: { level2: { leaf: 'ok' } } },
  invalid_missing_level1: {},
  invalid_missing_level2: { level1: {} },
  invalid_missing_leaf: { level1: { level2: {} } },
} satisfies Record<string, ConfigurationData>;

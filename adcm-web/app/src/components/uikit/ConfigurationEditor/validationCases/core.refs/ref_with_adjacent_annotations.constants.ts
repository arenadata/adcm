import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const ref_with_adjacent_annotations_description =
  'refs: $ref + соседние аннотации (title/description/default). Проверяем, что соседние аннотации рядом с $ref не ломают валидацию и редактирование поля.';

export const ref_with_adjacent_annotations_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core refs: $ref with adjacent annotations',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value (annotated)',
      description: 'Validation comes from $ref; title/description/default are adjacent annotations.',
      // Adjacent annotations (should not affect validation outcome)
      default: 7,
      $ref: '#/$defs/atLeastFive',
      // UI hint: ConfigurationEditor does not dereference $ref for choosing control
      type: 'integer',
      readOnly: false,
    },
  },
  required: ['value'],
  $defs: {
    atLeastFive: {
      type: 'integer',
      minimum: 5,
      readOnly: false,
    },
  },
};

export const ref_with_adjacent_annotations_datasets = {
  valid_minimum_5: { value: 5 },
  invalid_below_minimum_5: { value: 4 },
  invalid_missing_required_value: {},
} satisfies Record<string, ConfigurationData>;

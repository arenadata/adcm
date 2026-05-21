import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const discriminator_value_not_in_mapping_description =
  'discriminator: discriminator value не соответствует ни одной ветке (не совпадает с const в oneOf) — ветка не выбирается, должны быть ошибки (аналог unknown selection).';

export const discriminator_value_not_in_mapping_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: selection not in mapping',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    variant: {
      title: 'variant',
      type: 'object',
      readOnly: false,
      discriminator: { propertyName: '_selection' },
      oneOf: [
        {
          type: 'object',
          additionalProperties: false,
          required: ['_selection', 'text'],
          properties: {
            _selection: { const: 'str', title: '_selection' },
            text: { title: 'text', type: 'string', readOnly: false },
          },
        },
        {
          type: 'object',
          additionalProperties: false,
          required: ['_selection', 'num'],
          properties: {
            _selection: { const: 'num', title: '_selection' },
            num: { title: 'num', type: 'integer', readOnly: false },
          },
        },
      ],
    },
  },
  required: ['variant'],
};

export const discriminator_value_not_in_mapping_datasets = {
  wrong_selection_value: {
    variant: { _selection: 'str_typo', text: 'hello' },
  },
  wrong_selection_value_with_other_field: {
    variant: { _selection: 'num_typo', num: 1 },
  },
} satisfies Record<string, ConfigurationData>;

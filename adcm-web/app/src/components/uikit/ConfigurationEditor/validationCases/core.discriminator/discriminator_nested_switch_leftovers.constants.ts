import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const discriminator_nested_switch_leftovers_description =
  'discriminator: nested discriminator + leftovers — смена ветки во вложенном объекте; “лишние” поля от другой ветки должны быть ошибкой.';

export const discriminator_nested_switch_leftovers_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: nested switch + leftovers',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    section: {
      title: 'section',
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
                text: { title: 'text', type: 'string', readOnly: false, minLength: 1 },
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
    },
  },
  required: ['section'],
};

export const discriminator_nested_switch_leftovers_datasets = {
  valid_nested_str: {
    section: { variant: { _selection: 'str', text: 'ok' } },
  },
  valid_nested_num: {
    section: { variant: { _selection: 'num', num: 1 } },
  },
  nested_str_with_num_leftover: {
    section: { variant: { _selection: 'str', text: 'ok', num: 1 } },
  },
  nested_num_with_text_leftover: {
    section: { variant: { _selection: 'num', num: 1, text: 'ok' } },
  },
} satisfies Record<string, ConfigurationData>;

import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const discriminator_nested_path_description =
  'discriminator: discriminator во вложенном объекте — проверяем корректные пути ошибок и построение дерева на глубоком уровне.';

export const discriminator_nested_path_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: nested discriminator path',
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
          discriminator: {
            propertyName: '_selection',
          },
          oneOf: [
            {
              type: 'object',
              additionalProperties: false,
              required: ['_selection', 'text'],
              properties: {
                _selection: { const: 'str', title: '_selection' },
                text: { title: 'text', type: 'string', readOnly: false, minLength: 3 },
              },
            },
            {
              type: 'object',
              additionalProperties: false,
              required: ['_selection', 'num'],
              properties: {
                _selection: { const: 'num', title: '_selection' },
                num: { title: 'num', type: 'integer', readOnly: false, minimum: 10 },
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

export const discriminator_nested_path_datasets = {
  missing_discriminator_nested: {
    section: {
      variant: {
        text: 'hello',
      },
    },
  },
  str_branch_missing_required_nested: {
    section: {
      variant: {
        _selection: 'str',
      },
    },
  },
  num_branch_invalid_payload_nested: {
    section: {
      variant: {
        _selection: 'num',
        num: 1,
      },
    },
  },
} satisfies Record<string, ConfigurationData>;

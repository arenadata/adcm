import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const discriminator_switch_branch_leftovers_description =
  'discriminator: смена discriminator-ветки — проверяем, что поля от другой ветки становятся ошибкой (additionalProperties:false) и не “прячутся” при выборе ветки.';

export const discriminator_switch_branch_leftovers_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: switch branch and leftovers',
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
            _selection: {
              const: 'str',
              title: '_selection',
            },
            text: {
              title: 'text',
              type: 'string',
              readOnly: false,
              minLength: 1,
            },
          },
        },
        {
          type: 'object',
          additionalProperties: false,
          required: ['_selection', 'num'],
          properties: {
            _selection: {
              const: 'num',
              title: '_selection',
            },
            num: {
              title: 'num',
              type: 'integer',
              readOnly: false,
            },
          },
        },
      ],
    },
  },
  required: ['variant'],
};

export const discriminator_switch_branch_leftovers_datasets = {
  valid_str: {
    variant: {
      _selection: 'str',
      text: 'ok',
    },
  },
  valid_num: {
    variant: {
      _selection: 'num',
      num: 1,
    },
  },
  str_with_num_leftover: {
    variant: {
      _selection: 'str',
      text: 'ok',
      num: 1,
    },
  },
  num_with_text_leftover: {
    variant: {
      _selection: 'num',
      num: 1,
      text: 'ok',
    },
  },
} satisfies Record<string, ConfigurationData>;

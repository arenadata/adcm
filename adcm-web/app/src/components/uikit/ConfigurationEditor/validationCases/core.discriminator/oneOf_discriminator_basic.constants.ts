import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const oneOf_discriminator_basic_description =
  'discriminator: oneOf + discriminator — базовый кейс: ветка выбирается по _selection, валидация идёт по выбранной ветке.';

export const oneOf_discriminator_basic_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: oneOf + discriminator (basic)',
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

export const oneOf_discriminator_basic_datasets = {
  valid_branch_str: {
    variant: {
      _selection: 'str',
      text: 'hello',
    },
  },
  valid_branch_num: {
    variant: {
      _selection: 'num',
      num: 42,
    },
  },
  invalid_wrong_payload_for_str_branch: {
    variant: {
      _selection: 'str',
      num: 1,
    },
  },
  invalid_unknown_discriminator: {
    variant: {
      _selection: 'other',
      text: 'x',
    },
  },
} satisfies Record<string, ConfigurationData>;

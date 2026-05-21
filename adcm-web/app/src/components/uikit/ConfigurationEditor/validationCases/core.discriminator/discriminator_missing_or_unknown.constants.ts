import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const discriminator_missing_or_unknown_description =
  'discriminator: oneOf + discriminator — проверяем missing/unknown discriminator и ошибки required внутри выбранной ветки.';

export const discriminator_missing_or_unknown_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: missing/unknown selection + branch required',
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
              minLength: 3,
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
              minimum: 10,
            },
          },
        },
      ],
    },
  },
  required: ['variant'],
};

export const discriminator_missing_or_unknown_datasets = {
  missing_discriminator: {
    variant: {
      text: 'hello',
    },
  },
  unknown_discriminator: {
    variant: {
      _selection: 'other',
      text: 'hello',
    },
  },
  str_branch_missing_required: {
    variant: {
      _selection: 'str',
    },
  },
  str_branch_invalid_payload: {
    variant: {
      _selection: 'str',
      text: 'x',
    },
  },
  num_branch_invalid_payload: {
    variant: {
      _selection: 'num',
      num: 1,
    },
  },
} satisfies Record<string, ConfigurationData>;

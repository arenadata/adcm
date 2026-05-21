import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const nullable_discriminator_object_description =
  "discriminator: discriminator-object с type: ['object','null'] — variant может быть null и это ВАЛИДНО по JSON Schema; при null не должно ломаться построение UI (ветка не выбрана). При отсутствии variant — required-ошибка.";

export const nullable_discriminator_object_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: nullable discriminator object',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    variant: {
      title: 'variant',
      type: ['object', 'null'],
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
      ],
    },
  },
  required: ['variant'],
};

export const nullable_discriminator_object_datasets = {
  variant_missing_required_error: {},
  variant_null_allowed_no_branch: { variant: null },
  variant_object_missing_discriminator: {
    variant: { text: 'hello' },
  },
} satisfies Record<string, ConfigurationData>;

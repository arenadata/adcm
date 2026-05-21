import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const discriminator_null_forbidden_description =
  'discriminator: discriminator-object без null — variant должен быть объектом; variant:null даёт ошибку type.';

export const discriminator_null_forbidden_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: null forbidden',
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
      ],
    },
  },
  required: ['variant'],
};

export const discriminator_null_forbidden_datasets = {
  variant_null_type_error: { variant: null },
} satisfies Record<string, ConfigurationData>;

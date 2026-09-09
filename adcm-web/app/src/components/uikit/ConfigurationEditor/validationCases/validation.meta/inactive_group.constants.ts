import type { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const inactive_group_description =
  'meta: при attributes[path].isActive === false ошибки под этим узлом и потомками удаляются (filterConfigurationErrors).';

export const inactive_group_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation meta: inactive group hides errors',
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
        field: {
          title: 'field',
          type: 'string',
          minLength: 10,
          readOnly: false,
        },
      },
      required: ['field'],
    },
  },
  required: ['section'],
};

export const inactive_group_datasets = {
  errors_visible: { section: { field: 'short' } },
  errors_suppressed: { section: { field: 'short' } },
} satisfies Record<string, ConfigurationData>;

export const inactive_group_attributesByDataset: Record<string, ConfigurationAttributes> = {
  errors_visible: {},
  errors_suppressed: {
    '/section': { isActive: false },
  },
};

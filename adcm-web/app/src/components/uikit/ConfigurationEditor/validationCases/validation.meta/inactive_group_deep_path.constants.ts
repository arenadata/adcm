import type { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const inactive_group_deep_path_description =
  "meta: при attributes['/section/sub'].isActive === false ошибки под этим узлом и потомками (например '/section/sub/leaf') удаляются (filterConfigurationErrors).";

export const inactive_group_deep_path_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation meta: inactive group on deep path hides errors',
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
        sub: {
          title: 'sub',
          type: 'object',
          readOnly: false,
          additionalProperties: false,
          properties: {
            leaf: {
              title: 'leaf',
              type: 'string',
              minLength: 10,
              readOnly: false,
            },
          },
          required: ['leaf'],
        },
      },
      required: ['sub'],
    },
  },
  required: ['section'],
};

export const inactive_group_deep_path_datasets = {
  errors_visible: { section: { sub: { leaf: 'short' } } },
  errors_suppressed: { section: { sub: { leaf: 'short' } } },
} satisfies Record<string, ConfigurationData>;

export const inactive_group_deep_path_attributesByDataset: Record<string, ConfigurationAttributes> = {
  errors_visible: {},
  errors_suppressed: {
    '/section/sub': { isActive: false },
  },
};

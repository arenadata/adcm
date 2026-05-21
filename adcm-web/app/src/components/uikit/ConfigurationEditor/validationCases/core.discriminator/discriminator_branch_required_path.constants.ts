import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const discriminator_branch_required_path_description =
  'discriminator: required внутри выбранной ветки — проверяем, что ошибка не “теряется” на уровне variant и видна на ожидаемом leaf пути.';

export const discriminator_branch_required_path_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core discriminator: required inside selected branch',
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
          required: ['_selection', 'cfg'],
          properties: {
            _selection: {
              const: 'with_cfg',
              title: '_selection',
            },
            cfg: {
              title: 'cfg',
              type: 'object',
              readOnly: false,
              additionalProperties: false,
              required: ['enabled'],
              properties: {
                enabled: {
                  title: 'enabled',
                  type: 'boolean',
                  readOnly: false,
                },
              },
            },
          },
        },
        {
          type: 'object',
          additionalProperties: false,
          required: ['_selection', 'name'],
          properties: {
            _selection: {
              const: 'with_name',
              title: '_selection',
            },
            name: {
              title: 'name',
              type: 'string',
              readOnly: false,
              minLength: 3,
            },
          },
        },
      ],
    },
  },
  required: ['variant'],
};

export const discriminator_branch_required_path_datasets = {
  missing_required_nested_in_selected_branch: {
    variant: {
      _selection: 'with_cfg',
      cfg: {},
    },
  },
  missing_required_object_itself: {
    variant: {
      _selection: 'with_cfg',
    },
  },
  other_branch_missing_required_leaf: {
    variant: {
      _selection: 'with_name',
    },
  },
} satisfies Record<string, ConfigurationData>;

import type { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const synchronized_readonly_ui_description =
  'meta: attributes[path].isSynchronized (на поле или на родителе) делает поле readonly в UI, но валидация JSON Schema не отключается — ошибка остаётся при невалидных данных.';

export const synchronized_readonly_ui_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation meta: synchronized (readonly UI) does not disable validation',
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
        note: {
          title: 'note',
          type: 'string',
          minLength: 5,
          readOnly: false,
        },
      },
      required: ['note'],
    },
  },
  required: ['section'],
};

export const synchronized_readonly_ui_datasets = {
  not_synchronized_errors_visible: { section: { note: 'ab' } },
  synchronized_on_leaf_errors_visible: { section: { note: 'ab' } },
  synchronized_on_parent_errors_visible: { section: { note: 'ab' } },
} satisfies Record<string, ConfigurationData>;

export const synchronized_readonly_ui_attributesByDataset: Record<string, ConfigurationAttributes> = {
  not_synchronized_errors_visible: {},
  synchronized_on_leaf_errors_visible: {
    '/section/note': { isSynchronized: true },
  },
  synchronized_on_parent_errors_visible: {
    '/section': { isSynchronized: true },
  },
};

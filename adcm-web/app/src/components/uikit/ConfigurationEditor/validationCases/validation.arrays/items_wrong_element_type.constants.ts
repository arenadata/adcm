import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const items_wrong_element_type_description =
  'arrays: items задаёт string — ошибка типа должна указывать на индекс элемента (например /list/1).';

export const items_wrong_element_type_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: items type mismatch by index',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    list: {
      title: 'list',
      type: 'array',
      readOnly: false,
      items: { type: 'string' },
    },
  },
  required: ['list'],
};

export const items_wrong_element_type_datasets = {
  valid_all_strings: { list: ['a', 'b'] },
  invalid_second_element_number: { list: ['a', 2] },
} satisfies Record<string, ConfigurationData>;

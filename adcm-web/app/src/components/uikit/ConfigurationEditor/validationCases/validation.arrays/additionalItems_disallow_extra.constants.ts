import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const additionalItems_disallow_extra_description =
  'arrays: `additionalItems` с `prefixItems` (deprecated в 2020-12; тест для сравнения/совместимости). ' +
  'Дополнительные элементы массива запрещены, а также ключ `additionalItems` в текущем strict-режиме может давать ошибку на уровне схемы. ' +
  'В сторибуке ожидаем, что все датасеты будут невалидными.';

export const additionalItems_disallow_extra_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation arrays: additionalItems disallow extra',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    arr: {
      title: 'arr',
      type: 'array',
      readOnly: false,
      prefixItems: [{ type: 'integer' }, { type: 'integer' }],
      // For extra items beyond prefixItems.
      additionalItems: false,
    },
  },
  required: ['arr'],
};

export const additionalItems_disallow_extra_datasets = {
  invalid_exact_prefix_still_should_fail: { arr: [1, 2] },
  invalid_has_extra_item: { arr: [1, 2, 3] },
  invalid_wrong_type_in_prefix: { arr: [1, 'x'] },
} satisfies Record<string, ConfigurationData>;

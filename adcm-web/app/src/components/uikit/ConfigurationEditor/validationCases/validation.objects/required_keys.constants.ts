import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const required_keys_description = 'objects: required — обязательные имена свойств верхнего уровня.';

export const required_keys_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation objects: required',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    id: { title: 'id', type: 'string', readOnly: false },
    label: { title: 'label', type: 'string', readOnly: false },
    extra: { title: 'extra', type: 'string', readOnly: false },
  },
  required: ['id', 'label'],
};

export const required_keys_datasets = {
  valid_both_required_present: { id: 'x', label: 'y' },
  valid_with_optional: { id: 'x', label: 'y', extra: 'z' },
  invalid_missing_required: { id: 'x' },
} satisfies Record<string, ConfigurationData>;

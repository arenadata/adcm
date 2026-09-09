import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const dependentRequired_basic_description =
  'deps: dependentRequired. Если указали `credit_card`, обязательно должен быть `billing_address`.';

export const dependentRequired_basic_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core deps: dependentRequired (basic)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    credit_card: { title: 'credit_card', type: 'string', readOnly: false },
    billing_address: { title: 'billing_address', type: 'string', readOnly: false },
  },
  dependentRequired: {
    credit_card: ['billing_address'],
  },
};

export const dependentRequired_basic_datasets = {
  valid_empty_object_passes: {},
  valid_credit_card_with_billing_address_passes: { credit_card: '4111', billing_address: 'Street 1' },
  invalid_credit_card_missing_billing_address: { credit_card: '4111' },
} satisfies Record<string, ConfigurationData>;

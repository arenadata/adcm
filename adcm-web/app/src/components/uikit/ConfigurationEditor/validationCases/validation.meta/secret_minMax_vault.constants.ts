import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const secret_minMax_vault_description =
  'meta: adcmMeta.isSecret — для plain-строки ошибки minLength/maxLength/pattern видны; значение с префиксом $ANSIBLE_VAULT (хеш с бэкенда) снимает minLength/maxLength/pattern в filterConfigurationErrors.';

export const secret_minMax_vault_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation meta: secret + min/max/pattern vs vault hash',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    password: {
      title: 'password',
      type: 'string',
      minLength: 5,
      maxLength: 8,
      pattern: '^[0-9]+$',
      adcmMeta: {
        isSecret: true,
      },
    },
  },
  required: ['password'],
};

export const secret_minMax_vault_datasets = {
  plain_invalid_constraints: { password: 'abc' },
  vault_hash_constraints_suppressed: { password: '$ANSIBLE_VAULT$1$2$3$4$5$6$7$8$9$0' },
} satisfies Record<string, ConfigurationData>;

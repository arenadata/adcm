import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const secret_pattern_vault_description =
  'meta: adcmMeta.isSecret — для plain-строки видна ошибка pattern; значение с префиксом $ANSIBLE_VAULT (хеш с бэкенда) снимает pattern/minLength/maxLength в filterConfigurationErrors.';

export const secret_pattern_vault_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation meta: secret + pattern vs vault hash',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    password: {
      title: 'password',
      type: 'string',
      readOnly: false,
      pattern: '^[0-9]+$',
      adcmMeta: {
        isSecret: true,
      },
    },
  },
  required: ['password'],
};

export const secret_pattern_vault_datasets = {
  plain_invalid_pattern: { password: 'abc' },
  vault_hash_pattern_suppressed: { password: '$ANSIBLE_VAULT$1$2$3$4$5$6$7$8$9$0' },
} satisfies Record<string, ConfigurationData>;

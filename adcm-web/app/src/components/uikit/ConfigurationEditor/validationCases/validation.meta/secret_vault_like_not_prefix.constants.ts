import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const secret_vault_like_not_prefix_description =
  'meta: adcmMeta.isSecret — строка похожа на vault-хеш, но не начинается с $ANSIBLE_VAULT; ошибки minLength/maxLength/pattern не должны подавляться (проверка startsWith).';

export const secret_vault_like_not_prefix_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation meta: secret + vault-like but not prefix',
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

export const secret_vault_like_not_prefix_datasets = {
  vault_like_but_not_prefix_errors_visible: { password: 'xx$ANSIBLE_VAULT$1$2$3' },
} satisfies Record<string, ConfigurationData>;

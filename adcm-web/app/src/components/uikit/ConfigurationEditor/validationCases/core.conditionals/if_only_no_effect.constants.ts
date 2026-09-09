import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const if_only_no_effect_description =
  'if без then/else: результат if не должен влиять на итоговую валидность. Проверяем, что и flag=true и flag=false проходят.';

export const if_only_no_effect_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core conditionals: if-only (no effect)',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    flag: { title: 'flag', type: 'boolean', readOnly: false },
  },
  if: {
    properties: { flag: { const: true } },
  },
  // Empty schemas keep the overall behavior "no effect".
  // biome-ignore lint/suspicious/noThenProperty: JSON Schema keyword `then`.
  then: {},
  else: {},
};

export const if_only_no_effect_datasets = {
  valid_flag_true: { flag: true },
  valid_flag_false: { flag: false },
  valid_flag_missing: {},
} satisfies Record<string, ConfigurationData>;

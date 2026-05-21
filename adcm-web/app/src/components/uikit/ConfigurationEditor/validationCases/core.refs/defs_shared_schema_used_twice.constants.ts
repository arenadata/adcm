import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const defs_shared_schema_used_twice_description =
  'refs: один $defs используется в двух свойствах. Проверяем, что ошибки подсвечиваются на разных путях (/a и /b) при общей схеме в $defs.';

export const defs_shared_schema_used_twice_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core refs: shared $defs schema used twice',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    a: {
      title: 'a',
      description: 'Must match ^[a-z]+$',
      $ref: '#/$defs/lowercaseWord',
      type: 'string',
      readOnly: false,
    },
    b: {
      title: 'b',
      description: 'Must match ^[a-z]+$',
      $ref: '#/$defs/lowercaseWord',
      type: 'string',
      readOnly: false,
    },
  },
  required: ['a', 'b'],
  $defs: {
    lowercaseWord: {
      type: 'string',
      pattern: '^[a-z]+$',
      readOnly: false,
    },
  },
};

export const defs_shared_schema_used_twice_datasets = {
  valid_both_fields_ok: { a: 'abc', b: 'def' },
  invalid_a_fails_pattern: { a: 'ABC', b: 'def' },
  invalid_b_fails_pattern: { a: 'abc', b: '123' },
} satisfies Record<string, ConfigurationData>;

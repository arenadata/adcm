import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const ref_with_adjacent_type_conflict_description =
  'refs: $ref + конфликтующий type. Фиксируем ожидаемое поведение валидатора (должно быть невалидно, если adjacent keywords учитываются вместе с $ref).';

export const ref_with_adjacent_type_conflict_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Core refs: $ref with adjacent type conflict',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  properties: {
    value: {
      title: 'value',
      description:
        'If validator applies adjacent keywords with $ref, type:string conflicts with $ref(integer) -> always invalid.',
      $ref: '#/$defs/integerValue',
      // Intentionally conflicting with referenced schema
      type: 'string',
      readOnly: false,
    },
  },
  required: ['value'],
  $defs: {
    integerValue: {
      type: 'integer',
      readOnly: false,
    },
  },
};

export const ref_with_adjacent_type_conflict_datasets = {
  invalid_number_fails_type_string: { value: 1 },
  invalid_string_fails_ref_integer: { value: '1' },
} satisfies Record<string, ConfigurationData>;

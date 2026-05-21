import type { ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const minProperties_maxProperties_description =
  'objects: объект с minProperties и maxProperties (число ключей в экземпляре).';

export const minProperties_maxProperties_schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  title: 'Validation objects: minProperties + maxProperties',
  type: 'object',
  readOnly: false,
  additionalProperties: false,
  minProperties: 2,
  maxProperties: 2,
  properties: {
    a: { title: 'a', type: 'string', readOnly: false },
    b: { title: 'b', type: 'string', readOnly: false },
    c: { title: 'c', type: 'string', readOnly: false },
  },
};

export const minProperties_maxProperties_datasets = {
  valid_exactly_two_keys: { a: '1', b: '2' },
  invalid_too_few_keys: { a: 'only' },
  invalid_too_many_keys: { a: '1', b: '2', c: '3' },
} satisfies Record<string, ConfigurationData>;

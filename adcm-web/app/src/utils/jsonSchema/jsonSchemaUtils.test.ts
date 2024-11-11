import type { Schema } from 'ajv/dist/2020';
import { validate, generateFromSchema } from './jsonSchemaUtils';

describe('validate', () => {
  const schema: Schema = {
    $schema: 'https://json-schema.org/draft/2020-12/schema',
    type: 'object',
    required: ['clusterConfiguration'],
    readOnly: false,
    properties: {
      clusterConfiguration: {
        title: 'Cluster Configuration',
        description: '',
        type: 'object',
        required: ['cluster_config'],
        properties: {
          cluster_config: {
            type: 'object',
            required: ['cluster'],
            properties: {
              cluster: {
                title: 'cluster',
                type: 'object',
                required: ['cluster_name'],
                additionalProperties: false,
                properties: {
                  cluster_name: {
                    title: 'cluster_name',
                    type: 'string',
                  },
                  shard: {
                    type: 'array',
                    description: 'List of shards',
                    items: {
                      description: 'shard',
                      type: 'object',
                      required: ['internal_replica', 'weight'],
                      properties: {
                        internal_replica: {
                          type: 'integer',
                          minimum: 12,
                        },
                        weight: {
                          type: 'integer',
                          maximum: 10,
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        },
      },
    },
  };

  test('validate correct data', () => {
    const object = {
      clusterConfiguration: {
        cluster_config: {
          cluster: {
            cluster_name: 'cluster',
            shard: [{ internal_replica: 15, weight: 10 }],
          },
        },
      },
    };

    const errors = validate(schema, object);
    expect(errors).toBe(null);
  });

  test('validate incorrect data', () => {
    const object = {
      clusterConfiguration: {
        cluster_config: {
          cluster: {
            cluster_name: 'cluster',
            shard: [{ internal_replica: 11, weight: 11 }],
          },
        },
      },
    };

    const errors = validate(schema, object);

    expect(errors).not.toBe(null);
    expect(errors?.length).toBe(2);
    expect(errors![0].instancePath).toBe('/clusterConfiguration/cluster_config/cluster/shard/0/internal_replica');
    expect(errors![0].message).toBe('must be >= 12');
    expect(errors![1].instancePath).toBe('/clusterConfiguration/cluster_config/cluster/shard/0/weight');
    expect(errors![1].message).toBe('must be <= 10');
  });

  test('validate multiple types', () => {
    const schema: Schema = {
      $schema: 'https://json-schema.org/draft/2020-12/schema',
      type: 'object',
      required: ['cluster_config'],
      properties: {
        cluster_config: {
          anyOf: [
            { type: 'null' },
            {
              type: 'object',
              required: ['cluster_name'],
              properties: {
                cluster_name: {
                  title: 'cluster_name',
                  type: 'string',
                  readOnly: false,
                },
              },
            },
          ],
        },
      },
    };

    const object1 = {
      cluster_config: {
        cluster_name: 'cluster',
      },
    };

    const object2 = {
      cluster_config: null,
    };

    const object3 = {
      some_field: null,
    };

    const errors1 = validate(schema, object1);
    expect(errors1).toBe(null);

    const errors2 = validate(schema, object2);
    expect(errors2).toBe(null);

    const errors3 = validate(schema, object3);
    expect(errors3).not.toBe(null);
  });
});

describe('generateFromSchema', () => {
  test('generate structure with defaults', () => {
    const schema: Schema = {
      description: 'shard',
      type: 'object',
      required: ['internal_replica', 'weight'],
      properties: {
        internal_replica: {
          type: 'integer',
          maximum: 10,
          default: 1000,
        },
        weight: {
          type: 'integer',
          minimum: 12,
          default: 100,
        },
      },
    };

    const object = { internal_replica: 1000, weight: 100 };

    const result = generateFromSchema(schema);
    expect(result).toStrictEqual(object);
  });

  test('generate nullable primitive with defaults', () => {
    const schema: Schema = {
      oneOf: [
        {
          type: 'boolean',
          title: '',
          description: '',
          default: false,
          readOnly: false,
          adcmMeta: {
            isAdvanced: false,
            isInvisible: false,
            activation: null,
            synchronization: null,
            isSecret: false,
            stringExtra: null,
            enumExtra: null,
          },
        },
        {
          type: 'null',
        },
      ],
    };

    const result = generateFromSchema(schema);
    expect(result).toStrictEqual(null);
  });

  test('generate primitive with defaults', () => {
    const schema: Schema = {
      type: 'boolean',
      title: '',
      description: '',
      default: true,
      readOnly: false,
      adcmMeta: {
        isAdvanced: false,
        isInvisible: false,
        activation: null,
        synchronization: null,
        isSecret: false,
        stringExtra: null,
        enumExtra: null,
      },
    };

    const result = generateFromSchema(schema);
    expect(result).toStrictEqual(true);
  });

  test('validate unsafe_pattern', () => {
    const schema: Schema = {
      $schema: 'https://json-schema.org/draft/2020-12/schema',
      type: 'object',
      required: ['cluster_config'],
      properties: {
        cluster_config: {
          type: 'object',
          required: ['cluster_name', 'cluster_description'],
          properties: {
            cluster_name: {
              title: 'cluster_name',
              type: 'string',
              readOnly: false,
              pattern: '[a-',
            },
            cluster_description: {
              title: 'cluster_name',
              type: 'string',
              readOnly: false,
              pattern: '[a-*',
            },
          },
        },
      },
    };

    const object = {
      cluster_config: {
        cluster_name: '1',
        cluster_description: 'aaaaaaa',
      },
    };

    const errors3 = validate(schema, object);
    expect(errors3).not.toBe(null);
  });

  test('validate pattern', () => {
    const schema: Schema = {
      $schema: 'https://json-schema.org/draft/2020-12/schema',
      type: 'object',
      required: ['cluster_config'],
      properties: {
        cluster_config: {
          type: 'object',
          required: ['cluster_name'],
          properties: {
            cluster_name: {
              title: 'cluster_name',
              type: 'string',
              readOnly: false,
              pattern: '[a-z]',
            },
          },
        },
      },
    };

    const object = {
      cluster_config: {
        cluster_name: '1',
      },
    };

    const errors3 = validate(schema, object);
    expect(errors3).not.toBe(null);
  });
});

import { Schema } from 'ajv/dist/2020';
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

    const result = validate(schema, object);
    expect(result.isValid).toBe(true);
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

    const result = validate(schema, object);
    expect(result.isValid).toBe(false);
    expect(result.errorsPaths).toStrictEqual({
      '/clusterConfiguration': true,
      '/clusterConfiguration/cluster_config': true,
      '/clusterConfiguration/cluster_config/cluster': true,
      '/clusterConfiguration/cluster_config/cluster/shard': true,
      '/clusterConfiguration/cluster_config/cluster/shard/0': true,
      '/clusterConfiguration/cluster_config/cluster/shard/0/internal_replica': 'must be >= 12',
      '/clusterConfiguration/cluster_config/cluster/shard/0/weight': 'must be <= 10',
    });
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

    const result1 = validate(schema, object1);
    expect(result1.isValid).toBe(true);

    const result2 = validate(schema, object2);
    expect(result2.isValid).toBe(true);

    const result3 = validate(schema, object3);
    expect(result3.isValid).toBe(false);
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
});

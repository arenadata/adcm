import type { Schema } from '@cfworker/json-schema';

import { validate, generateFromSchema, type SchemaLike } from './jsonSchemaUtils';

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

  test('validateOneOfSchema', () => {
    const schema: Schema = {
      $schema: 'https://json-schema.org/draft/2020-12/schema',
      type: 'object',
      additionalProperties: false,
      properties: {
        'catalog.manager': {
          default: {
            static: {},
          },
          oneOf: [
            {
              type: 'object',
              readOnly: false,
              properties: {
                dynamic: {
                  type: 'object',
                  default: {},
                  readOnly: false,
                  properties: {
                    'catalog.store': {
                      type: 'string',
                      description: '',
                      default: 'file',
                      readOnly: false,
                    },
                  },
                  required: ['catalog.store'],
                },
              },
              required: ['dynamic'],
            },

            {
              type: 'object',
              readOnly: false,
              properties: {
                static: {
                  type: 'object',
                  default: {},
                  readOnly: false,
                  properties: {
                    'file.store': {
                      type: 'number',
                      description: '',
                      default: 'file',
                      readOnly: false,
                    },
                  },
                  required: ['file.store'],
                },
              },
              required: ['static'],
            },

            {
              type: 'null',
            },
          ],
        },
      },
    };

    const object1 = {
      'catalog.manager': {
        dynamic: {
          'catalog.store': '/var/abc',
        },
      },
    };

    const errors1 = validate(schema, object1);
    expect(errors1).toBe(null);

    const object2 = {
      'catalog.manager': {
        static: {
          'file.store': 1,
        },
      },
    };

    const errors2 = validate(schema, object2);
    expect(errors2).toBe(null);

    const object3 = {
      'catalog.manager': null,
    };

    const errors3 = validate(schema, object3);
    expect(errors3).toBe(null);
  });

  test('validate with discriminator', () => {
    const schema = {
      type: 'object',
      required: ['catalog.manager'],
      properties: {
        'catalog.manager': {
          type: 'object',
          discriminator: { propertyName: 'catalog.type' },
          default: {
            'catalog.type': 'static',
          },
          required: ['catalog.type'],
          oneOf: [
            {
              properties: {
                'catalog.type': {
                  const: 'dynamic',
                  title: 'adjajdkasjdlasjdls',
                  type: 'string',
                },
                dynamic: {
                  type: 'object',
                  default: {
                    foo: 'qqq',
                  },
                  properties: {
                    foo: {
                      type: 'string',
                      default: 'aaa',
                    },
                  },
                },
              },
              required: ['dynamic'],
            },
            {
              properties: {
                'catalog.type': {
                  const: 'static',
                  type: 'string',
                },
                static: {
                  type: 'object',
                  default: {
                    bar: 100,
                  },
                  properties: {
                    bar: {
                      type: 'number',
                      default: 10,
                    },
                  },
                },
              },
              required: ['static'],
            },
          ],
        },
      },
    };

    const oneOfData = {
      'catalog.manager': {
        'catalog.type': 'static',
        static: {
          bar: 100,
        },
      },
    };

    const errors = validate(schema, oneOfData);
    expect(errors).toBe(null);
  });

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
    expect(errors![0].message).toBe('11 is less than 12.');
    expect(errors![1].instancePath).toBe('/clusterConfiguration/cluster_config/cluster/shard/0/weight');
    expect(errors![1].message).toBe('11 is greater than 10.');
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
      default: null,
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

  test('generate primitive with no defaults', () => {
    const schema: Schema = {
      type: 'boolean',
      title: '',
      description: '',
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
    expect(result).toStrictEqual(undefined);
  });

  test('validate user scenario with required + nullable branches', () => {
    const schema = {
      title: 'Configuration',
      type: 'object',
      properties: {
        float: {
          oneOf: [
            {
              title: 'float',
              default: 0.1,
              adcmMeta: { isAdvanced: false, isInvisible: false, isSecret: false },
              type: 'number',
            },
            { type: 'null' },
          ],
          default: 0.1,
        },
        string: {
          oneOf: [
            {
              title: 'string',
              default: 'test',
              adcmMeta: { isAdvanced: false, isInvisible: false, isSecret: false },
              type: 'string',
            },
            { type: 'null' },
          ],
          default: 'test',
        },
        password: {
          oneOf: [
            {
              title: 'password',
              default: null,
              adcmMeta: { isAdvanced: true, isInvisible: false, isSecret: true },
              type: 'string',
              minLength: 1,
            },
            { type: 'null' },
          ],
          default: null,
        },
      },
      required: ['float', 'string', 'password'],
      additionalProperties: false,
      $schema: 'https://json-schema.org/draft/2020-12/schema',
    } as SchemaLike;

    const data = {
      my_float: 0.1,
      my_string: 'string',
      my_password: null,
    };

    const errors = validate(schema, data);
    expect(errors).not.toBeNull();
    expect(errors?.length).toBeGreaterThan(0);
    const paths = errors!.map((e) => e.instancePath);
    expect(paths).toContain('/float');
    expect(paths).toContain('/string');
    expect(paths).toContain('/password');
  });

  test('generate object with discriminator', () => {
    const schema = {
      type: 'object',
      properties: {
        'catalog.manager': {
          type: 'object',
          discriminator: { propertyName: 'catalog.type' },
          default: {
            'catalog.type': 'static',
          },
          required: ['catalog.type'],
          oneOf: [
            {
              properties: {
                'catalog.type': { const: 'dynamic', title: 'adjajdkasjdlasjdls' },
                dynamic: {
                  type: 'object',
                  default: {
                    foo: 'qqq',
                  },
                  properties: {
                    foo: {
                      type: 'string',
                      default: 'aaa',
                    },
                  },
                },
              },
              required: ['dynamic'],
            },
            {
              properties: {
                'catalog.type': { const: 'static' },
                static: {
                  type: 'object',
                  default: {
                    bar: 100,
                  },
                  properties: {
                    bar: {
                      type: 'number',
                      default: 10,
                    },
                  },
                },
              },
              required: ['static'],
            },
          ],
        },
      },
    };

    const result = generateFromSchema(schema);
    expect(result).toStrictEqual({
      'catalog.manager': {
        'catalog.type': 'static',
        static: {
          bar: 100,
        },
      },
    });
  });

  test('generate object with nullable discriminator', () => {
    const schema: Schema = {
      type: 'object',
      properties: {
        'catalog.manager': {
          default: {
            myType: 'static',
            static: {
              bar: -100,
            },
          },
          oneOf: [
            {
              type: 'null',
            },
            {
              type: 'object',
              discriminator: { propertyName: 'myType' },
              default: {
                myType: 'static',
              },
              required: ['myType'],
              oneOf: [
                {
                  properties: {
                    myType: { const: 'dynamic', title: 'Dynamic title' },
                    dynamic: {
                      type: 'object',
                      default: {
                        foo: 'qqq',
                      },
                      properties: {
                        foo: {
                          type: 'string',
                          default: 'aaa',
                        },
                      },
                      required: ['foo'],
                    },
                  },
                  required: ['dynamic'],
                },
                {
                  properties: {
                    myType: { const: 'static', title: 'Dynamic title' },
                    static: {
                      type: 'object',
                      default: {
                        bar: 100,
                      },
                      properties: {
                        bar: {
                          type: 'number',
                          default: 10,
                        },
                      },
                      required: ['bar'],
                    },
                  },
                  required: ['static'],
                },
              ],
            },
          ],
        },
      },
    };

    const result = generateFromSchema(schema);

    // default value from "catalog.manager"
    expect(result).toStrictEqual({
      'catalog.manager': {
        myType: 'static',
        static: {
          bar: -100,
        },
      },
    });
  });

  test('generate object with defaults', () => {
    const schema: Schema = {
      $schema: 'https://json-schema.org/draft/2020-12/schema',
      type: 'object',
      additionalProperties: false,
      properties: {
        myRoot: {
          type: 'object',
          default: {
            myInt: 100,
            myStr: 'zxcvbn',
          },
          properties: {
            myInt: {
              type: 'number',
              default: 1,
            },
            myStr: {
              type: 'string',
              default: 'qwert',
            },
          },
        },
      },
    };

    const result = generateFromSchema(schema);
    expect(result).toStrictEqual({
      myRoot: {
        myInt: 100,
        myStr: 'zxcvbn',
      },
    });
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

  test('discriminated oneOf: missing required nested field gets leaf instancePath', () => {
    const schema: Schema = {
      type: 'object',
      properties: {
        group: {
          type: 'object',
          discriminator: { propertyName: '_selection' },
          oneOf: [
            {
              type: 'object',
              properties: {
                _selection: { const: 'a', type: 'string' },
                a: {
                  type: 'object',
                  required: ['plain'],
                  properties: { plain: { type: 'integer', default: 1 } },
                },
              },
              required: ['_selection', 'a'],
            },
          ],
        },
      },
    };

    const errors = validate(schema, { group: { _selection: 'a', a: {} } });
    expect(errors).not.toBe(null);
    expect(errors!.some((e) => e.instancePath === '/group/a/plain' && e.keyword === 'required')).toBe(true);
  });
});

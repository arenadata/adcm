import type { ConfigurationAttributes, ConfigurationSchema } from '@models/adcm';

export const adcmConfigurationSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  title: 'Primary configuration',
  required: ['cluster_config'],
  readOnly: false,
  properties: {
    cluster_config: {
      type: 'object',
      title: 'Cluster configuration',
      description: '',
      additionalProperties: false,
      readOnly: false,
      adcmMeta: {
        activation: {
          isAllowChange: true,
        },
        synchronization: {
          isAllowChange: true,
        },
      },
      default: {
        cluster: [
          {
            cluster_name: 'default cluster name',
            shard: [],
          },
        ],
      },
      required: ['some_field3', 'cluster'],
      properties: {
        some_field: {
          type: 'number',
          title: 'SOME FIELD !!!',
          description: 'SOME DESCR',
          readOnly: false,
          adcmMeta: {
            activation: {
              isAllowChange: true,
            },
            synchronization: {
              isAllowChange: true,
            },
          },
        },
        some_field2: {
          type: 'number',
          title: 'Some field 2',
          readOnly: false,
          adcmMeta: {
            isAdvanced: true,
            activation: {
              isAllowChange: true,
            },
            synchronization: {
              isAllowChange: true,
            },
          },
        },
        some_field3: {
          type: 'number',
          readOnly: false,
          adcmMeta: {
            isInvisible: true,
            activation: {
              isAllowChange: true,
            },
            synchronization: {
              isAllowChange: true,
            },
          },
        },
        cluster: {
          type: 'array',
          readOnly: false,
          title: 'Custer',
          adcmMeta: {
            activation: {
              isAllowChange: true,
            },
            synchronization: {
              isAllowChange: true,
            },
          },
          items: {
            type: 'object',
            additionalProperties: false,
            readOnly: false,
            required: ['cluster_name', 'cluster_password'],
            properties: {
              cluster_name: {
                type: 'string',
                title: 'Cluster name',
                default: 'default cluster name',
                readOnly: false,
                maxLength: 10,
              },
              cluster_password: {
                title: 'Password',
                type: 'string',
                pattern: '^[a-z]*$',
                default: 'default cluster password [a-z]',
                readOnly: false,
                maxLength: 10,
                adcmMeta: {
                  isSecret: true,
                },
              },
              shard: {
                type: 'array',
                title: 'Shards',
                default: [],
                readOnly: false,
                items: {
                  type: 'object',
                  additionalProperties: false,
                  readOnly: false,
                  required: ['weight', 'internal_replica', 'replicas', 'secret_field'],
                  properties: {
                    weight: {
                      type: 'integer',
                      title: 'Weight',
                      description: 'some weight description',
                      default: 10,
                      readOnly: false,
                    },
                    secret_field: {
                      type: 'string',
                      title: 'Secret field',
                      description: 'some weight description',
                      default: '',
                      readOnly: false,
                      adcmMeta: {
                        isInvisible: true,
                      },
                    },
                    internal_replica: {
                      type: 'integer',
                      title: 'Internal replica',
                      default: 11,
                      readOnly: false,
                    },
                    replicas: {
                      type: 'array',
                      default: [{ host: 'test_test' }],
                      readOnly: false,
                      title: 'Replicas',
                      items: {
                        type: 'object',
                        additionalProperties: false,
                        readOnly: false,
                        required: ['host'],
                        properties: {
                          host: {
                            type: 'string',
                            default: 'default-host',
                            title: 'Host name',
                            readOnly: false,
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
    },
  },
};

export const adcmAttributes: ConfigurationAttributes = {
  '/cluster_config/some_field': {
    isActive: true,
    isSynchronized: false,
  },
  '/cluster_config/cluster': {
    isActive: true,
    isSynchronized: false,
  },
};

export const adcmSwappedAttributes: ConfigurationAttributes = {
  '/Cluster configuration/some_field': {
    isActive: true,
    isSynchronized: false,
  },
  '/Cluster configuration/Cluster': {
    isActive: true,
    isSynchronized: false,
  },
};

export const adcmConfig = {
  cluster_config: {
    some_field: 111,
    cluster: [
      {
        cluster_name: 'default',
        cluster_password: 'my password',
        shard: [
          {
            weight: 10,
            internal_replica: 11,
            secret_field: '***',
            replicas: [{ host: 'default-host' }],
          },
        ],
      },
    ],
    some_field2: 111,
    some_field3: 111,
  },
};

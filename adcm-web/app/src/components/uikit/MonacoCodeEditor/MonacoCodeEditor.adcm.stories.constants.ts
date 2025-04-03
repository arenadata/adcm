import type { ConfigurationAttributes, ConfigurationSchema } from '@models/adcm';

export const adcmConfigurationSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  title: 'Primary configuration',
  required: ['cluster_config'],
  readOnly: false,
  adcmMeta: {
    isAdvanced: false,
    isInvisible: false,
    activation: null,
    synchronization: null,
    isSecret: false,
    stringExtra: null,
  },
  properties: {
    cluster_config: {
      type: 'object',
      title: 'Cluster configuration',
      description: '',
      additionalProperties: false,
      readOnly: false,
      adcmMeta: {
        isAdvanced: false,
        isInvisible: false,
        activation: {
          isAllowChange: true,
        },
        synchronization: {
          isAllowChange: true,
        },
        isSecret: false,
        stringExtra: null,
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
            isAdvanced: false,
            isInvisible: false,
            activation: {
              isAllowChange: true,
            },
            synchronization: {
              isAllowChange: true,
            },
            isSecret: false,
            stringExtra: null,
          },
        },
        some_field2: {
          type: 'number',
          title: 'Some field 2',
          readOnly: false,
          adcmMeta: {
            isAdvanced: true,
            isInvisible: false,
            activation: {
              isAllowChange: true,
            },
            synchronization: {
              isAllowChange: true,
            },
            isSecret: false,
            stringExtra: null,
          },
        },
        some_field3: {
          type: 'number',
          readOnly: false,
          adcmMeta: {
            isAdvanced: false,
            isInvisible: true,
            activation: {
              isAllowChange: true,
            },
            synchronization: {
              isAllowChange: true,
            },
            isSecret: false,
            stringExtra: null,
          },
        },
        cluster: {
          type: 'array',
          readOnly: false,
          title: 'Custer',
          adcmMeta: {
            isAdvanced: false,
            isInvisible: false,
            activation: {
              isAllowChange: true,
            },
            synchronization: {
              isAllowChange: true,
            },
            isSecret: false,
            stringExtra: null,
          },
          items: {
            type: 'object',
            additionalProperties: false,
            readOnly: false,
            adcmMeta: {
              isAdvanced: false,
              isInvisible: false,
              activation: null,
              synchronization: null,
              isSecret: false,
              stringExtra: null,
            },
            required: ['cluster_name', 'cluster_password'],
            properties: {
              cluster_name: {
                type: 'string',
                title: 'Cluster name',
                default: 'default cluster name',
                readOnly: false,
                maxLength: 10,
                adcmMeta: {
                  isAdvanced: false,
                  isInvisible: false,
                  activation: null,
                  synchronization: null,
                  isSecret: false,
                  stringExtra: null,
                },
              },
              cluster_password: {
                title: 'Password',
                type: 'string',
                pattern: '^[a-z]*$',
                default: 'default cluster password [a-z]',
                readOnly: false,
                maxLength: 10,
                adcmMeta: {
                  isAdvanced: false,
                  isInvisible: false,
                  activation: null,
                  synchronization: null,
                  isSecret: true,
                  stringExtra: {
                    isMultiline: false,
                  },
                },
              },
              shard: {
                type: 'array',
                title: 'Shards',
                default: [],
                readOnly: false,
                adcmMeta: {
                  isAdvanced: false,
                  isInvisible: false,
                  activation: null,
                  synchronization: null,
                  isSecret: false,
                  stringExtra: null,
                },
                items: {
                  type: 'object',
                  additionalProperties: false,
                  readOnly: false,
                  adcmMeta: {
                    isAdvanced: false,
                    isInvisible: false,
                    activation: null,
                    synchronization: null,
                    isSecret: false,
                    stringExtra: null,
                  },
                  required: ['weight', 'internal_replica', 'replicas', 'secret_field'],
                  properties: {
                    weight: {
                      type: 'integer',
                      title: 'Weight',
                      description: 'some weight description',
                      default: 10,
                      readOnly: false,
                      adcmMeta: {
                        isAdvanced: false,
                        isInvisible: false,
                        activation: null,
                        synchronization: null,
                        isSecret: false,
                        stringExtra: null,
                      },
                    },
                    secret_field: {
                      type: 'string',
                      title: 'Secret field',
                      description: 'some weight description',
                      default: '',
                      readOnly: false,
                      adcmMeta: {
                        isAdvanced: false,
                        isInvisible: true,
                        activation: null,
                        synchronization: null,
                        isSecret: false,
                        stringExtra: null,
                      },
                    },
                    internal_replica: {
                      type: 'integer',
                      title: 'Internal replica',
                      default: 11,
                      readOnly: false,
                      adcmMeta: {
                        isAdvanced: false,
                        isInvisible: false,
                        activation: null,
                        synchronization: null,
                        isSecret: false,
                        stringExtra: null,
                      },
                    },
                    replicas: {
                      type: 'array',
                      default: [{ host: 'test_test' }],
                      readOnly: false,
                      title: 'Replicas',
                      adcmMeta: {
                        isAdvanced: false,
                        isInvisible: false,
                        activation: null,
                        synchronization: null,
                        isSecret: false,
                        stringExtra: null,
                      },
                      items: {
                        type: 'object',
                        additionalProperties: false,
                        readOnly: false,
                        adcmMeta: {
                          isAdvanced: false,
                          isInvisible: false,
                          activation: null,
                          synchronization: null,
                          isSecret: false,
                          stringExtra: null,
                        },
                        required: ['host'],
                        properties: {
                          host: {
                            type: 'string',
                            default: 'default-host',
                            title: 'Host name',
                            readOnly: false,
                            adcmMeta: {
                              isAdvanced: false,
                              isInvisible: false,
                              activation: null,
                              synchronization: null,
                              isSecret: false,
                              stringExtra: null,
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

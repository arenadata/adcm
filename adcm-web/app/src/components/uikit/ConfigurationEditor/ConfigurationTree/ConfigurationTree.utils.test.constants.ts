import { ConfigurationSchema } from '@models/adcm';

export const schema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  title: 'Cluster Configuration',
  required: ['cluster_config'],
  readOnly: false,
  adcmMeta: {
    isAdvanced: false,
    activation: null,
    synchronization: null,

    stringExtra: null,
  },
  properties: {
    cluster_config: {
      type: 'object',
      readOnly: true,
      adcmMeta: {
        isAdvanced: false,
        activation: null,
        synchronization: null,

        stringExtra: null,
      },
      required: ['cluster'],
      additionalProperties: false,
      properties: {
        cluster: {
          title: 'cluster',
          type: 'object',
          readOnly: true,
          adcmMeta: {
            isAdvanced: false,
            activation: null,
            synchronization: null,

            stringExtra: null,
          },
          required: ['cluster_name'],
          additionalProperties: false,
          properties: {
            cluster_name: {
              title: 'Cluster Name',
              type: 'string',
              readOnly: true,
              adcmMeta: {
                isAdvanced: false,
                activation: null,
                synchronization: null,

                stringExtra: null,
              },
            },
            shard: {
              type: 'array',
              title: 'List of shards',
              readOnly: false,
              adcmMeta: {
                isAdvanced: false,
                activation: null,
                synchronization: null,

                stringExtra: null,
              },
              items: {
                title: 'shard',
                type: 'object',
                required: ['internal_replica', 'weight'],
                readOnly: false,
                additionalProperties: false,
                adcmMeta: {
                  isAdvanced: false,
                  activation: null,
                  synchronization: null,

                  stringExtra: null,
                },
                properties: {
                  weight: {
                    type: 'integer',
                    maximum: 10,
                    default: 0,
                    readOnly: false,
                    adcmMeta: {
                      isAdvanced: false,
                      activation: null,
                      synchronization: null,

                      stringExtra: null,
                    },
                  },
                  internal_replica: {
                    type: 'integer',
                    minimum: 12,
                    default: 0,
                    readOnly: false,
                    adcmMeta: {
                      isAdvanced: false,
                      activation: null,
                      synchronization: null,

                      stringExtra: null,
                    },
                  },
                },
              },
            },
          },
        },
        deletable_field: {
          type: 'integer',
          minimum: 12,
          default: 0,
          readOnly: false,
          adcmMeta: {
            isAdvanced: false,
            activation: null,
            synchronization: null,

            stringExtra: null,
          },
        },
        auth: {
          readOnly: false,
          adcmMeta: {
            isAdvanced: false,
            activation: null,
            synchronization: null,

            stringExtra: null,
          },
          type: 'object',
          required: ['token', 'expire'],
          additionalProperties: true,
          properties: {
            token: {
              type: 'string',
              readOnly: false,
              adcmMeta: {
                isAdvanced: false,
                activation: null,
                synchronization: null,

                stringExtra: null,
              },
            },
            expire: {
              type: 'number',
              readOnly: false,
              adcmMeta: {
                isAdvanced: false,
                activation: null,
                synchronization: null,

                stringExtra: null,
              },
            },
          },
        },
      },
    },
  },
};

export const configuration = {
  cluster_config: {
    cluster: {
      cluster_name: 'Lorem ipsum cluster',
      shard: [
        { internal_replica: 11, weight: 11 },
        { internal_replica: 110, weight: 110 },
      ],
    },
    auth: {
      token: 'test',
      expire: 10,
    },
    deletable_field: 11,
  },
};

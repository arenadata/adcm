import type { ConfigurationSchema } from '@models/adcm';
import type { ConfigurationTreeFilter } from '../ConfigurationEditor.types';

export const emptyFilter: ConfigurationTreeFilter = { title: '', showAdvanced: true, showInvisible: true };

export const clusterConfigurationSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  title: 'Cluster Configuration',
  required: ['cluster_config'],
  readOnly: false,
  properties: {
    cluster_config: {
      type: 'object',
      readOnly: true,
      required: ['cluster'],
      additionalProperties: false,
      properties: {
        cluster: {
          title: 'cluster',
          type: 'object',
          readOnly: true,
          required: ['cluster_name'],
          additionalProperties: false,
          properties: {
            cluster_name: {
              title: 'Cluster Name',
              type: 'string',
              readOnly: true,
            },
            shard: {
              type: 'array',
              title: 'List of shards',
              readOnly: false,
              items: {
                title: 'shard',
                type: 'object',
                required: ['internal_replica', 'weight'],
                readOnly: false,
                additionalProperties: false,
                properties: {
                  weight: {
                    type: 'integer',
                    maximum: 10,
                    default: 0,
                    readOnly: false,
                  },
                  internal_replica: {
                    type: 'integer',
                    minimum: 12,
                    default: 0,
                    readOnly: false,
                  },
                },
              },
            },
          },
        },
        auth: {
          readOnly: false,
          type: 'object',
          required: ['token', 'expire'],
          additionalProperties: true,
          properties: {
            token: {
              type: 'string',
              readOnly: false,
            },
            expire: {
              type: 'number',
              readOnly: false,
            },
          },
        },
      },
    },
  },
};

export const clusterConfiguration = {
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
  },
};

export const defaultProps = {
  readOnly: false,
};

export const structureSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['structure'],
  ...defaultProps,
  properties: {
    structure: {
      type: 'object',
      ...defaultProps,
      required: ['someField1', 'someField2'],
      additionalProperties: false,
      properties: {
        someField1: {
          type: 'string',
          ...defaultProps,
        },
        someField2: {
          type: 'string',
          ...defaultProps,
        },
      },
    },
  },
};

export const structureSchemaWithTitle: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['structure'],
  ...defaultProps,
  properties: {
    structure: {
      type: 'object',
      title: 'Structure title',
      ...defaultProps,
      required: ['someField1', 'someField2'],
      additionalProperties: false,
      properties: {
        someField1: {
          type: 'string',
          ...defaultProps,
        },
        someField2: {
          type: 'string',
          ...defaultProps,
        },
      },
    },
  },
};

export const nullableStructureSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['structure'],
  ...defaultProps,
  properties: {
    structure: {
      oneOf: [
        { type: 'null' },
        {
          type: 'object',
          ...defaultProps,
          required: ['someField1', 'someField2'],
          additionalProperties: false,
          properties: {
            someField1: {
              type: 'string',
              ...defaultProps,
            },
          },
        },
      ],
    },
  },
};

export const mapSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['map'],
  ...defaultProps,
  properties: {
    map: {
      type: 'object',
      ...defaultProps,
      additionalProperties: true,
      properties: {},
    },
  },
};

export const nullableMapSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['map'],
  ...defaultProps,
  properties: {
    map: {
      oneOf: [
        { type: 'null' },
        {
          type: 'object',
          ...defaultProps,
          additionalProperties: true,
          properties: {
            someField1: {
              type: 'string',
              ...defaultProps,
            },
          },
        },
      ],
    },
  },
};

export const readonlyMapSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['map'],
  ...defaultProps,
  properties: {
    map: {
      type: 'object',
      ...defaultProps,
      additionalProperties: true,
      readOnly: true,
      properties: {},
    },
  },
};

export const mapSchemaWithPredefinedData: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['map'],
  ...defaultProps,
  properties: {
    map: {
      type: 'object',
      ...defaultProps,
      additionalProperties: true,
      required: ['someField1', 'someField2'],
      properties: {
        someField1: {
          type: 'string',
          ...defaultProps,
        },
        someField2: {
          type: 'string',
          ...defaultProps,
        },
      },
    },
  },
};

export const listSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['list'],
  ...defaultProps,
  properties: {
    list: {
      type: 'array',
      ...defaultProps,
      additionalProperties: true,
      items: {
        type: 'string',
        ...defaultProps,
      },
    },
  },
};

export const nullableListSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['list'],
  ...defaultProps,
  properties: {
    list: {
      oneOf: [
        { type: 'null' },
        {
          type: 'array',
          ...defaultProps,
          items: {
            type: 'string',
            ...defaultProps,
          },
        },
      ],
    },
  },
};

export const listSchemaWithTitle: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['list'],
  ...defaultProps,
  properties: {
    list: {
      oneOf: [
        { type: 'null' },
        {
          type: 'array',
          title: 'Strings',
          ...defaultProps,
          items: {
            type: 'string',
            ...defaultProps,
          },
        },
      ],
    },
  },
};

export const readonlyListSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['list'],
  ...defaultProps,
  properties: {
    list: {
      type: 'array',
      ...defaultProps,
      readOnly: true,
      additionalProperties: true,
      items: {
        type: 'string',
        ...defaultProps,
      },
    },
  },
};

export const fieldSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['someField1'],
  ...defaultProps,
  properties: {
    someField1: {
      type: 'string',
      ...defaultProps,
    },
  },
};

export const nullableFieldSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['someField1'],
  ...defaultProps,
  properties: {
    someField1: {
      oneOf: [
        { type: 'null' },
        {
          type: 'string',
          ...defaultProps,
        },
      ],
    },
  },
};

export const readonlyFieldSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['someField1'],
  ...defaultProps,
  properties: {
    someField1: {
      type: 'string',
      ...defaultProps,
      readOnly: true,
    },
  },
};

export const fieldSchemaWithTitle: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['someField1'],
  ...defaultProps,
  properties: {
    someField1: {
      type: 'string',
      title: 'Field title',
      ...defaultProps,
    },
  },
};

export const validateInactiveGroupSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['structure', 'structure_2'],
  ...defaultProps,
  properties: {
    structure: {
      type: 'object',
      ...defaultProps,
      properties: {
        someField1: { type: 'string', ...defaultProps },
      },
    },
    structure_2: {
      type: 'object',
      ...defaultProps,
      properties: {
        someField1: { type: 'string', ...defaultProps },
      },
    },
  },
};

export const validateNestedErrorsSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['structure', 'structure_2'],
  ...defaultProps,
  properties: {
    list: {
      oneOf: [
        {
          type: 'null',
        },
        {
          type: 'array',
          ...defaultProps,
          title: '',
          description: '',
          default: [],
          readOnly: false,
          items: {
            ...defaultProps,
            type: 'string',
            title: '',
            description: '',
            default: null,
            readOnly: false,
          },
          minItems: 1,
        },
      ],
    },
  },
};

export const selectableObjectSchema: ConfigurationSchema = {
  title: 'Configuration',
  description: '',
  readOnly: false,
  type: 'object',
  properties: {
    selectable_no_default_required: {
      title: 'selectable_no_default_required',
      description: '',
      readOnly: false,
      default: null,
      type: 'object',
      discriminator: {
        propertyName: '_selection',
      },
      oneOf: [
        {
          required: ['_selection', 'a'],
          additionalProperties: false,
          properties: {
            _selection: {
              const: 'a',
              title: 'a',
            },
            a: {
              title: 'a',
              description: '',
              readOnly: false,
              default: {},
              type: 'object',
              additionalProperties: false,
              properties: {
                plain: {
                  title: 'plain',
                  description: '',
                  readOnly: false,
                  default: 2,
                  type: 'integer',
                },
              },
              required: ['plain'],
            },
          },
        },
        {
          required: ['_selection', 'b'],
          additionalProperties: false,
          properties: {
            _selection: {
              const: 'b',
              title: 'b',
            },
            b: {
              title: 'b',
              description: '',
              readOnly: false,
              default: {},
              type: 'object',
              additionalProperties: false,
              properties: {
                plain: {
                  title: 'plain',
                  description: '',
                  readOnly: false,
                  default: 2,
                  type: 'integer',
                },
              },
              required: ['plain'],
            },
          },
        },
      ],
    },
  },
  required: ['selectable_no_default_required'],
  additionalProperties: false,
  $schema: 'https://json-schema.org/draft/2020-12/schema',
};

export const selectableObjectConfig = {
  selectable_no_default_required: {
    _selection: 'a',
    a: {
      plain: 2,
    },
  },
};

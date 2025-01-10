export const schema = {
  type: 'object',
  required: ['some_field'],
  properties: {
    some_enum: {
      type: 'string',
      enum: ['up', 'down', 'left', 'right'],
    },
    some_optional: {
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
    },
    some_field: {
      type: 'string',
      description: 'some field. Required',
      adcmMeta: {
        isAdvanced: false,
        isInvisible: false,
        activation: null,
        synchronization: null,
        isSecret: false,
        stringExtra: null,
        enumExtra: null,
      },
      readOnly: true,
    },
    some_structure: {
      type: 'object',
      default: {},
      readOnly: true,
      adcmMeta: {
        isAdvanced: false,
        isInvisible: false,
        activation: null,
        synchronization: null,

        isSecret: false,
        stringExtra: null,
        enumExtra: null,
      },
      additionalProperties: false,
      properties: {
        key1: {
          type: 'string',
          adcmMeta: {
            isAdvanced: false,
            isInvisible: false,
            activation: null,
            synchronization: null,
            isSecret: false,
            stringExtra: null,
            enumExtra: null,
          },
          readOnly: true,
        },
      },
    },
    some_map: {
      type: 'object',
      default: {},
      readOnly: true,
      adcmMeta: {
        isAdvanced: false,
        isInvisible: false,
        activation: null,
        synchronization: null,
        isSecret: false,
        stringExtra: null,
        enumExtra: null,
      },
      additionalProperties: true,
      properties: {},
    },
    some_array: {
      type: 'array',
      default: [],
      description: 'some description',
      readOnly: true,
      adcmMeta: {
        isAdvanced: false,
        isInvisible: false,
        activation: null,
        synchronization: null,

        isSecret: false,
        stringExtra: null,
        enumExtra: null,
      },
      items: {
        type: 'object',
        adcmMeta: {
          isAdvanced: false,
          isInvisible: false,
          activation: null,
          synchronization: null,
          isSecret: false,
          stringExtra: null,
          enumExtra: null,
        },
        readOnly: true,
        required: ['field1', 'field2'],
        properties: {
          field1: {
            type: 'string',
            adcmMeta: {
              isAdvanced: false,
              isInvisible: false,
              activation: null,
              synchronization: null,
              isSecret: false,
              stringExtra: null,
              enumExtra: null,
            },
            readOnly: false,
          },
          field2: {
            type: 'number',
            description: 'field2 description',
            minimum: 10,
            default: 55,
            maximum: 100,
            adcmMeta: {
              isAdvanced: false,
              isInvisible: false,
              activation: null,
              synchronization: null,
              isSecret: false,
              stringExtra: null,
              enumExtra: null,
            },
            readOnly: false,
          },
        },
      },
    },
  },
};

export const jsonText = `{
  "some_field": "lorem",
  "some_structure": {
    "key1": "value1"
  },
  "some_map": {
    "mapEntry1": "123",
    "mapEntry2": "456"
  },
  "some_array": [{ "field1": "value" }]
}`;

export const yamlText = `some_field: value
some_structure: 
  key1: value1
  key2: value2
some_map:
  mapEntry1: 123
  mapEntry2: 456
some_array:
  - field1: value
    field2: some number here between 10 and 100
`;

export const mappingText = `mapping: 
  service 1:
    component 1:
      - host 1
  service 2:
    component 2:
      - host 1
`;

export const mappingSchema = {
  type: 'object',
  properties: {
    mapping: {
      type: 'object',
    },
  },
};

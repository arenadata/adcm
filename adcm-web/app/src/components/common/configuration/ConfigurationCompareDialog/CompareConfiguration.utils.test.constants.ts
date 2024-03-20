import { ConfigurationSchema } from '@models/adcm';
import { ConfigurationTreeFilter } from '@uikit/ConfigurationEditor/ConfigurationEditor.types';

export const emptyFilter: ConfigurationTreeFilter = { title: '', showAdvanced: true, showInvisible: true };

const defaultAdcmMeta = {
  isAdvanced: false,
  activation: null,
  synchronization: null,
  stringExtra: null,
};

const defaultProps = {
  readOnly: false,
  adcmMeta: { ...defaultAdcmMeta },
};

export const fieldSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['list'],
  ...defaultProps,
  properties: {
    someField: {
      title: 'Some field',
      type: 'string',
      ...defaultProps,
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
      title: 'Some array',
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

export const structureSchema: ConfigurationSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  required: ['structure'],
  ...defaultProps,
  properties: {
    structure: {
      title: 'Some structure',
      type: 'object',
      ...defaultProps,
      required: ['someField1', 'someField2'],
      additionalProperties: false,
      properties: {
        someField1: {
          title: 'Some field1',
          type: 'string',
          ...defaultProps,
        },
        someField2: {
          title: 'Some field2',
          type: 'string',
          ...defaultProps,
        },
      },
    },
  },
};

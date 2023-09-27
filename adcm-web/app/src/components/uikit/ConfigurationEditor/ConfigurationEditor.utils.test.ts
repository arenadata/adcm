import { SchemaDefinition } from '@models/adcm';
import {
  editField,
  addField,
  deleteField,
  addArrayItem,
  deleteArrayItem,
  removeEmpty,
} from './ConfigurationEditor.utils';

describe('modify configuration', () => {
  const object = {
    clusterConfiguration: {
      cluster_config: {
        cluster: {
          cluster_name: 'cluster',
          shard: [
            { internal_replica: 11, weight: 11 },
            { internal_replica: 12, weight: 12 },
          ],
        },
      },
    },
  };

  test('editField', () => {
    const result = editField(
      object,
      ['clusterConfiguration', 'cluster_config', 'cluster', 'shard', 0, 'internal_replica'],
      100,
    );

    expect(result).toStrictEqual({
      clusterConfiguration: {
        cluster_config: {
          cluster: {
            cluster_name: 'cluster',
            shard: [
              { internal_replica: 100, weight: 11 },
              { internal_replica: 12, weight: 12 },
            ],
          },
        },
      },
    });
  });

  test('addField', () => {
    const result = addField(object, ['clusterConfiguration', 'cluster_config', 'cluster', 'new_field'], 100);

    expect(result).toStrictEqual({
      clusterConfiguration: {
        cluster_config: {
          cluster: {
            cluster_name: 'cluster',
            new_field: 100,
            shard: [
              { internal_replica: 11, weight: 11 },
              { internal_replica: 12, weight: 12 },
            ],
          },
        },
      },
    });
  });

  test('deleteField', () => {
    const result = deleteField(object, ['clusterConfiguration', 'cluster_config', 'cluster', 'cluster_name']);

    expect(result).toStrictEqual({
      clusterConfiguration: {
        cluster_config: {
          cluster: {
            shard: [
              { internal_replica: 11, weight: 11 },
              { internal_replica: 12, weight: 12 },
            ],
          },
        },
      },
    });
  });

  test('addArrayItem', () => {
    const schema: SchemaDefinition = {
      description: 'shard',
      type: 'object',
      required: ['internal_replica', 'weight'],
      readOnly: false,
      additionalProperties: false,
      adcmMeta: {
        nullValue: null,
        activation: null,
        synchronization: null,
        stringExtra: null,
      },
      properties: {
        weight: {
          type: 'integer',
          maximum: 10,
          default: 10,
          readOnly: false,
          adcmMeta: {
            nullValue: null,
            activation: null,
            synchronization: null,
            stringExtra: null,
          },
        },
        internal_replica: {
          type: 'integer',
          minimum: 12,
          default: 10,
          readOnly: false,
          adcmMeta: {
            nullValue: null,
            activation: null,
            synchronization: null,
            stringExtra: null,
          },
        },
      },
    };

    const result = addArrayItem(object, ['clusterConfiguration', 'cluster_config', 'cluster', 'shard'], schema);

    expect(result).toStrictEqual({
      clusterConfiguration: {
        cluster_config: {
          cluster: {
            cluster_name: 'cluster',
            shard: [
              { internal_replica: 11, weight: 11 },
              { internal_replica: 12, weight: 12 },
              { internal_replica: 10, weight: 10 },
            ],
          },
        },
      },
    });
  });

  test('deleteArrayItem', () => {
    const result = deleteArrayItem(object, ['clusterConfiguration', 'cluster_config', 'cluster', 'shard', 0]);

    expect(result).toStrictEqual({
      clusterConfiguration: {
        cluster_config: {
          cluster: {
            cluster_name: 'cluster',
            shard: [{ internal_replica: 12, weight: 12 }],
          },
        },
      },
    });
  });
});

describe('removeEmpty', () => {
  const sample = {
    field1: 'test',
    field2: {
      field21: 123,
      field22: [
        {
          field221: 456,
          field222: undefined,
        },
      ],
    },
    field3: undefined,
    field4: [1, 2, 3, { someField: undefined }],
  };

  const expected = {
    field1: 'test',
    field2: {
      field21: 123,
      field22: [
        {
          field221: 456,
        },
      ],
    },
    field4: [1, 2, 3, {}],
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  expect(removeEmpty(sample as any)).toStrictEqual(expected);
});

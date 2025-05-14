import type { ConfigurationSchema, SchemaDefinition } from '@models/adcm';
import {
  editField,
  addField,
  deleteField,
  addArrayItem,
  deleteArrayItem,
  removeEmpty,
  moveArrayItem,
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

  const object5 = {
    clusterConfiguration: {
      cluster_config: {
        cluster: {
          cluster_name: 'cluster',
          shard: [
            { internal_replica: 11, weight: 11 },
            { internal_replica: 12, weight: 12 },
            { internal_replica: 13, weight: 13 },
            { internal_replica: 14, weight: 14 },
            { internal_replica: 15, weight: 15 },
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

  test('addField: nullable value', () => {
    const testObject = { nullableObject: null };
    const result = addField(testObject, ['nullableObject', 'testField'], 100);

    expect(result).toStrictEqual({
      nullableObject: {
        testField: 100,
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

  test('addArrayItem: nullable array', () => {
    const testObject = { nullableArray: null };
    const schema: ConfigurationSchema = {
      type: 'integer',
      minimum: 12,
      default: 10,
      readOnly: false,
      adcmMeta: {
        activation: null,
        synchronization: null,
        stringExtra: null,
      },
    };

    const result = addArrayItem(testObject, ['nullableArray'], schema);

    expect(result).toStrictEqual({
      nullableArray: [10],
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

  test('moveArrayItem: move backward array item', () => {
    const result = moveArrayItem(
      object5,
      ['clusterConfiguration', 'cluster_config', 'cluster', 'shard', 3],
      ['clusterConfiguration', 'cluster_config', 'cluster', 'shard', 0],
    );

    expect(result).toStrictEqual({
      clusterConfiguration: {
        cluster_config: {
          cluster: {
            cluster_name: 'cluster',
            shard: [
              { internal_replica: 14, weight: 14 },
              { internal_replica: 11, weight: 11 },
              { internal_replica: 12, weight: 12 },
              { internal_replica: 13, weight: 13 },
              { internal_replica: 15, weight: 15 },
            ],
          },
        },
      },
    });
  });

  test('moveArrayItem: move forward array item', () => {
    const result = moveArrayItem(
      object5,
      ['clusterConfiguration', 'cluster_config', 'cluster', 'shard', 2],
      ['clusterConfiguration', 'cluster_config', 'cluster', 'shard', 4],
    );

    expect(result).toStrictEqual({
      clusterConfiguration: {
        cluster_config: {
          cluster: {
            cluster_name: 'cluster',
            shard: [
              { internal_replica: 11, weight: 11 },
              { internal_replica: 12, weight: 12 },
              { internal_replica: 14, weight: 14 },
              { internal_replica: 15, weight: 15 },
              { internal_replica: 13, weight: 13 },
            ],
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

  // biome-ignore lint/suspicious/noExplicitAny:
  expect(removeEmpty(sample as any)).toStrictEqual(expected);
});

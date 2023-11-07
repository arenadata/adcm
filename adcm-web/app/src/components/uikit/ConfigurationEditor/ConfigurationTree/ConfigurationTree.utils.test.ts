/* eslint-disable @typescript-eslint/no-non-null-assertion */
/* eslint-disable @typescript-eslint/no-non-null-asserted-optional-chain */
import {
  clusterConfigurationSchema,
  clusterConfiguration,
  // structure schemas
  structureSchema,
  nullableStructureSchema,
  structureSchemaWithTitle,
  // map schemas
  mapSchema,
  nullableMapSchema,
  mapSchemaWithPredefinedData,
  readonlyMapSchema,
  // array schemas
  listSchema,
  nullableListSchema,
  listSchemaWithTitle,
  readonlyListSchema,
  // field schemas
  fieldSchema,
  nullableFieldSchema,
  fieldSchemaWithTitle,
  readonlyFieldSchema,
  // validate schemas
  validateInactiveGroupSchema,
} from './ConfigurationTree.utils.test.constants';
import { buildTreeNodes, filterTreeNodes, validate } from './ConfigurationTree.utils';
import { ConfigurationArray, ConfigurationField, ConfigurationObject } from '../ConfigurationEditor.types';
import { rootNodeKey } from './ConfigurationTree.constants';

describe('structure node tests', () => {
  test('structure', () => {
    const tree = buildTreeNodes(structureSchema, {}, {});
    const structureNode = tree.children?.[0]!;
    const structureNodeData = structureNode.data as ConfigurationObject;

    expect(structureNodeData.objectType).toBe('structure');
    expect(structureNodeData.isReadonly).toBe(false);
    expect(structureNodeData.isNullable).toBe(false);
    expect(structureNodeData.isCleanable).toBe(false);
  });

  test('nullable', () => {
    const configuration = {
      structure: null,
    };

    const tree = buildTreeNodes(nullableStructureSchema, configuration, {});
    const structureNode = tree.children?.[0]!;
    const structureNodeData = structureNode.data as ConfigurationObject;

    expect(structureNodeData.isNullable).toBe(true);
    expect(structureNodeData.isCleanable).toBe(true);
    expect(structureNodeData.fieldSchema.type === 'object');

    const setButtonNode = structureNode.children?.[0]!;

    expect(setButtonNode.data.type).toBe('addEmptyObject');
  });

  test('title', () => {
    const tree = buildTreeNodes(structureSchemaWithTitle, {}, {});
    const structureNodeWithTitle = tree.children?.[0]!;

    expect(structureNodeWithTitle.data.title).toBe('Structure title');

    const tree2 = buildTreeNodes(structureSchema, {}, {});
    const structureNodeWithDefaultTitle = tree2.children?.[0]!;

    expect(structureNodeWithDefaultTitle.data.title).toBe('structure');
  });

  test('structure fields', () => {
    const configuration = {
      structure: {
        someField1: 'value1',
        someField2: 'value2',
      },
    };
    const tree = buildTreeNodes(structureSchema, configuration, {});
    const structureNode = tree.children?.[0]!;

    expect(structureNode.children?.length).toBe(2);
    expect(structureNode.children?.[0].data.title).toBe('someField1');
    expect(structureNode.children?.[1].data.title).toBe('someField2');
  });
});

describe('map node tests', () => {
  test('map', () => {
    const tree = buildTreeNodes(mapSchema, {}, {});
    const mapNode = tree.children?.[0]!;
    const mapNodeData = mapNode.data as ConfigurationObject;

    expect(mapNodeData.objectType).toBe('map');
    expect(mapNodeData.isReadonly).toBe(false);
    expect(mapNodeData.isNullable).toBe(false);
    expect(mapNodeData.isCleanable).toBe(false);
    expect(mapNode.children?.length).toBe(1);
    expect(mapNode.children?.[0].data.type).toBe('addField');
  });

  test('nullable', () => {
    const tree = buildTreeNodes(nullableMapSchema, {}, {});
    const mapNode = tree.children?.[0]!;
    const mapNodeData = mapNode.data as ConfigurationObject;

    expect(mapNodeData.isNullable).toBe(true);
    expect(mapNodeData.isCleanable).toBe(true);
    expect(mapNodeData.fieldSchema.type === 'object');

    const addPropertyButtonNode = mapNode.children?.[0]!;

    expect(addPropertyButtonNode.data.type).toBe('addField');
  });

  test('map with data', () => {
    const config = { map: { someField1: 'someField1Value', someField2: 'someField2Value' } };
    const tree = buildTreeNodes(mapSchema, config, {});
    const mapNode = tree.children?.[0]!;
    const nodeData = mapNode.data as ConfigurationObject;

    expect(nodeData.isReadonly).toBe(false);
    expect(mapNode.children?.length).toBe(3);

    const field1NodeData = mapNode.children?.[0].data as ConfigurationField;
    expect(field1NodeData.value).toBe(config.map.someField1);
    expect(field1NodeData.isDeletable).toBe(true);

    const field2NodeData = mapNode.children?.[1].data as ConfigurationField;
    expect(field2NodeData.value).toBe(config.map.someField2);
    expect(field2NodeData.isDeletable).toBe(true);

    expect(mapNode.children?.[2].data.type).toBe('addField');
  });

  test('predefined data', () => {
    const config = { map: { someField1: 'someField1Value', someField2: 'someField2Value' } };
    const tree = buildTreeNodes(mapSchemaWithPredefinedData, config, {});
    const mapNode = tree.children?.[0]!;
    const nodeData = mapNode.data as ConfigurationObject;

    expect(nodeData.isReadonly).toBe(false);
    expect(mapNode.children?.length).toBe(3);

    const field1NodeData = mapNode.children?.[0].data as ConfigurationField;
    expect(field1NodeData.value).toBe(config.map.someField1);
    expect(field1NodeData.isDeletable).toBe(false);

    const field2NodeData = mapNode.children?.[1].data as ConfigurationField;
    expect(field2NodeData.value).toBe(config.map.someField2);
    expect(field2NodeData.isDeletable).toBe(false);

    expect(mapNode.children?.[2].data.type).toBe('addField');
  });

  test('readonly map', () => {
    const config = { map: { someField1: 'someField1Value', someField2: 'someField2Value' } };
    const tree = buildTreeNodes(readonlyMapSchema, config, {});
    const mapNode = tree.children?.[0]!;
    const nodeData = mapNode.data as ConfigurationObject;

    expect(nodeData.objectType).toBe('map');
    expect(nodeData.isReadonly).toBe(true);
    expect(mapNode.children?.length).toBe(2);

    const field1NodeData = mapNode.children?.[0].data as ConfigurationField;
    expect(field1NodeData.value).toBe(config.map.someField1);
    expect(field1NodeData.isDeletable).toBe(false);
    expect(field1NodeData.isReadonly).toBe(true);

    const field2NodeData = mapNode.children?.[1].data as ConfigurationField;
    expect(field2NodeData.value).toBe(config.map.someField2);
    expect(field2NodeData.isDeletable).toBe(false);
    expect(field2NodeData.isReadonly).toBe(true);
  });
});

describe('array node tests', () => {
  test('array', () => {
    const tree = buildTreeNodes(listSchema, {}, {});
    const arrayNode = tree.children?.[0]!;
    const arrayNodeData = arrayNode.data as ConfigurationArray;

    expect(arrayNodeData.type).toBe('array');
    expect(arrayNodeData.isNullable).toBe(false);
    expect(arrayNodeData.isCleanable).toBe(false);
  });

  test('nullable array', () => {
    const tree = buildTreeNodes(nullableListSchema, {}, {});
    const arrayNode = tree.children?.[0]!;
    const arrayNodeData = arrayNode.data as ConfigurationArray;

    expect(arrayNodeData.type).toBe('array');
    expect(arrayNodeData.isNullable).toBe(true);
    expect(arrayNodeData.isCleanable).toBe(true);
  });

  test('title', () => {
    const configuration = {
      list: ['value1', 'value2'],
    };
    const tree = buildTreeNodes(listSchemaWithTitle, configuration, {});
    const arrayNodeWithTitle = tree.children?.[0]!;
    const item1NodeWithTitle = arrayNodeWithTitle.children?.[0]!;

    expect(arrayNodeWithTitle.data.title).toBe('Strings');
    expect(item1NodeWithTitle.data.title).toBe('Strings [0]');

    const tree2 = buildTreeNodes(listSchema, configuration, {});
    const arrayNodeWithDefaultTitle = tree2.children?.[0]!;
    const item1NodeWithDefaultTitle = arrayNodeWithDefaultTitle.children?.[0]!;

    expect(arrayNodeWithDefaultTitle.data.title).toBe('list');
    expect(item1NodeWithDefaultTitle.data.title).toBe('list [0]');
  });

  test('empty array', () => {
    const tree = buildTreeNodes(listSchema, {}, {});
    const arrayNode = tree.children?.[0]!;

    expect(arrayNode.children?.length).toBe(1);
    expect(arrayNode.children?.[0].data.type).toBe('addArrayItem');
  });

  test('array with data', () => {
    const config = {
      list: ['value1', 'value2'],
    };
    const tree = buildTreeNodes(listSchema, config, {});
    const arrayNode = tree.children?.[0]!;
    const arrayNodeData = arrayNode.data as ConfigurationArray;

    expect(arrayNodeData.type).toBe('array');
    expect(arrayNodeData.isReadonly).toBe(false);
    expect(arrayNode.children?.length).toBe(3);

    const item1NodeData = arrayNode.children?.[0].data as ConfigurationField;
    expect(item1NodeData.value).toBe(config.list[0]);
    expect(item1NodeData.isDeletable).toBe(true);

    const item2NodeData = arrayNode.children?.[1].data as ConfigurationField;
    expect(item2NodeData.value).toBe(config.list[1]);
    expect(item2NodeData.isDeletable).toBe(true);

    expect(arrayNode.children?.[2].data.type).toBe('addArrayItem');
  });

  test('readonly array', () => {
    const config = {
      list: ['value1', 'value2'],
    };
    const tree = buildTreeNodes(readonlyListSchema, config, {});
    const arrayNode = tree.children?.[0]!;
    const arrayNodeData = arrayNode.data as ConfigurationArray;

    expect(arrayNodeData.type).toBe('array');
    expect(arrayNodeData.isReadonly).toBe(true);
    expect(arrayNode.children?.length).toBe(2);

    const item1NodeData = arrayNode.children?.[0].data as ConfigurationField;
    expect(item1NodeData.value).toBe(config.list[0]);
    expect(item1NodeData.isDeletable).toBe(false);
    expect(item1NodeData.isReadonly).toBe(true);

    const item2NodeData = arrayNode.children?.[1].data as ConfigurationField;
    expect(item2NodeData.value).toBe(config.list[1]);
    expect(item2NodeData.isDeletable).toBe(false);
    expect(item2NodeData.isReadonly).toBe(true);
  });
});

describe('field node', () => {
  test('field', () => {
    const tree = buildTreeNodes(fieldSchema, {}, {});
    const fieldNode = tree.children?.[0]!;
    const fieldNodeData = fieldNode.data as ConfigurationField;

    expect(fieldNode.children).toBe(undefined);
    expect(fieldNodeData.isDeletable).toBe(false);
    expect(fieldNodeData.isCleanable).toBe(false);
  });

  test('nullable field', () => {
    const tree = buildTreeNodes(nullableFieldSchema, {}, {});
    const fieldNode = tree.children?.[0]!;
    const fieldNodeData = fieldNode.data as ConfigurationField;

    expect(fieldNodeData.isNullable).toBe(true);
    expect(fieldNodeData.isCleanable).toBe(true);
    expect(fieldNodeData.fieldSchema.type === 'string');
  });

  test('title', () => {
    const tree = buildTreeNodes(fieldSchemaWithTitle, {}, {});
    const fieldNodeWithDefinedTitle = tree.children?.[0]!;

    expect(fieldNodeWithDefinedTitle.data.title).toBe('Field title');

    const tree2 = buildTreeNodes(fieldSchema, {}, {});
    const fieldNodeWithDefaultTitle = tree2.children?.[0]!;

    expect(fieldNodeWithDefaultTitle.data.title).toBe('someField1');
  });

  test('readonly field', () => {
    const tree = buildTreeNodes(readonlyFieldSchema, {}, {});
    const fieldNode = tree.children?.[0]!;
    const fieldNodeData = fieldNode.data as ConfigurationField;

    expect(fieldNodeData.isReadonly).toBe(true);
  });
});

describe('validate', () => {
  test('basic validation', () => {
    const attributes = {};

    const configuration = {
      cluster_config: {
        cluster: {
          cluster_name: null, // <-- must be an error
          shard: [],
        },
        auth: {
          token: 'test',
          expire: 10,
        },
      },
    };

    const { isValid, errorsPaths } = validate(clusterConfigurationSchema, configuration, attributes);
    expect(isValid).toBe(false);
    expect(Object.keys(errorsPaths).length).not.toBe(0);
  });

  test('Do not validate inactive groups', () => {
    const structureAttributes = { isActive: false, isSynchronized: false };

    const attributes = {
      '/structure': structureAttributes,
    };

    const configuration = {
      structure: {
        someField1: null, // <-- must be ignored
      },
      structure_2: {
        someField1: null,
      },
    };

    const { isValid, errorsPaths } = validate(validateInactiveGroupSchema, configuration, attributes);
    expect(isValid).toBe(false);
    expect(errorsPaths).toStrictEqual({ '/': true, '/structure_2': true, '/structure_2/someField1': 'must be string' });
  });
});

describe('filter', () => {
  test('find something', () => {
    const tree = buildTreeNodes(clusterConfigurationSchema, clusterConfiguration, {});
    const filteredTree = filterTreeNodes(tree, { title: 'Name', showAdvanced: false, showInvisible: false });
    const rootNode = filteredTree;

    expect(rootNode).not.toBe(undefined);
    expect(rootNode.key).toBe(rootNodeKey);
    expect(rootNode.children?.length).toBe(1);

    const clusterConfigNode = filteredTree.children?.[0]!;
    expect(clusterConfigNode.key).toBe('/cluster_config');
    expect(clusterConfigNode.children?.length).toBe(1);

    const clusterNode = clusterConfigNode.children?.[0]!;
    expect(clusterNode.key).toBe('/cluster_config/cluster');
    expect(clusterNode.children?.length).toBe(1);

    const clusterNameNode = clusterNode.children?.[0]!;
    expect(clusterNameNode.key).toBe('/cluster_config/cluster/cluster_name');
    expect(clusterNameNode.children).toBe(undefined);
  });
});

describe('fillFieldAttributes', () => {
  test('Fill Field Attributes', () => {
    const clusterConfigAttributes = { isActive: true, isSynchronized: true };
    const clusterAttributes = { isActive: true, isSynchronized: false };
    const authAttributes = { isActive: false, isSynchronized: true };

    const attributes = {
      '/cluster_config': clusterConfigAttributes,
      '/cluster_config/cluster': clusterAttributes,
      '/cluster_config/auth': authAttributes,
    };

    const tree = buildTreeNodes(clusterConfigurationSchema, clusterConfiguration, attributes);

    const rootNode = tree;

    const clusterConfigNode = rootNode.children?.[0]!;
    expect(clusterConfigNode.data.fieldAttributes).toStrictEqual(clusterConfigAttributes);

    const clusterNode = clusterConfigNode.children?.[0]!;
    expect(clusterNode.data.fieldAttributes).toStrictEqual(clusterAttributes);

    const authNode = clusterConfigNode.children?.[1]!;
    expect(authNode.data.fieldAttributes).toStrictEqual(authAttributes);
  });
});

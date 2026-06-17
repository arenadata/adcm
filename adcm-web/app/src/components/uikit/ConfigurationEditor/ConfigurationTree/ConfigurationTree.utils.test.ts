/* eslint-disable @typescript-eslint/no-non-null-asserted-optional-chain */
import {
  clusterConfiguration,
  clusterConfigurationSchema,
  defaultProps,
  emptyFilter,
  fieldSchema,
  fieldSchemaWithTitle,
  listSchema,
  listSchemaWithTitle,
  mapSchema,
  mapSchemaWithPredefinedData,
  nullableFieldSchema,
  nullableListSchema,
  nullableMapSchema,
  nullableStructureSchema,
  readonlyFieldSchema,
  readonlyListSchema,
  readonlyMapSchema,
  selectableObjectConfig,
  selectableObjectFieldSchemaWithUnionDefault,
  selectableObjectSchema,
  structureSchema,
  structureSchemaWithTitle,
  validateInactiveGroupSchema,
  validateNestedErrorsSchema,
} from './ConfigurationTree.utils.test.constants';
import { configurationValidationSchema } from './__fixtures__/configurationValidationSchema';
import configurationValidationData from './__fixtures__/configurationValidationData.json';
import {
  buildConfigurationNodes,
  buildConfigurationTree,
  getDefaultValue,
  getErrorsForTreeRow,
  getOneOfSchemaDefaults,
  hasFieldDefaultValue,
  resolveFieldDefaultValue,
  validate,
} from './ConfigurationTree.utils';
import type { ConfigurationArray, ConfigurationField, ConfigurationObject } from '../ConfigurationEditor.types';
import type { ConfigurationErrors, FieldErrors, SchemaDefinition } from '@models/adcm';
import type { JSONObject } from '@models/json';
import { validate as validateJsonSchema } from '@utils/jsonSchema/jsonSchemaUtils';
import { jsonSchemaValidationService } from '@utils/jsonSchema/JsonSchemaValidationService';
import {
  discriminatorFieldName,
  nestedPropsErrorKeyword,
  nestedPropsErrorMessage,
  rootNodeKey,
} from './ConfigurationTree.constants';

describe('structure node tests', () => {
  test('structure', () => {
    const tree = buildConfigurationNodes(structureSchema, {}, {});
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

    const tree = buildConfigurationNodes(nullableStructureSchema, configuration, {});
    const viewTree = buildConfigurationTree(tree, emptyFilter);
    const structureNode = viewTree.children?.[0]!;
    const structureNodeData = structureNode.data as ConfigurationObject;

    expect(structureNodeData.isNullable).toBe(true);
    expect(structureNodeData.isCleanable).toBe(true);
    expect(structureNodeData.fieldSchema.type === 'object');

    const setButtonNode = structureNode.children?.[0]!;

    expect(setButtonNode.data.type).toBe('addEmptyObject');
  });

  test('title', () => {
    const tree = buildConfigurationNodes(structureSchemaWithTitle, {}, {});
    const structureNodeWithTitle = tree.children?.[0]!;

    expect(structureNodeWithTitle.data.title).toBe('Structure title');

    const tree2 = buildConfigurationNodes(structureSchema, {}, {});
    const structureNodeWithDefaultTitle = tree2.children?.[0]!;

    expect(structureNodeWithDefaultTitle.data.title).toBe('structure');
  });

  test('default value', () => {
    const node: SchemaDefinition = { ...defaultProps, default: 'someValue' };
    const parentNode: SchemaDefinition = { ...defaultProps, default: { keyName: 'parentValue' } };
    expect(getDefaultValue('keyName', node, parentNode)).toBe('someValue');

    const node2: SchemaDefinition = { ...defaultProps, default: null };
    const parentNode2: SchemaDefinition = { ...defaultProps, default: { keyName: 'parentValue' } };
    expect(getDefaultValue('keyName', node2, parentNode2)).toBe('parentValue');

    const node3: SchemaDefinition = defaultProps;
    const parentNode3: SchemaDefinition = { ...defaultProps, default: { keyName: 'parentValue' } };
    expect(getDefaultValue('keyName', node3, parentNode3)).toBe('parentValue');
  });

  test('resolveFieldDefaultValue', () => {
    const fieldSchema: SchemaDefinition = { type: 'string', readOnly: false };

    expect(resolveFieldDefaultValue({ defaultValue: 'from-node', fieldSchema })).toBe('from-node');
    expect(resolveFieldDefaultValue({ fieldSchema: { ...fieldSchema, default: '' } })).toBe('');
    expect(resolveFieldDefaultValue({ fieldSchema })).toBeUndefined();
  });

  test('hasFieldDefaultValue', () => {
    const fieldSchema: SchemaDefinition = { type: 'string', readOnly: false };

    expect(hasFieldDefaultValue({ defaultValue: '', fieldSchema })).toBe(true);
    expect(hasFieldDefaultValue({ fieldSchema: { ...fieldSchema, default: '' } })).toBe(true);
    expect(hasFieldDefaultValue({ fieldSchema })).toBe(false);
  });

  test('structure fields', () => {
    const configuration = {
      structure: {
        someField1: 'value1',
        someField2: 'value2',
      },
    };
    const tree = buildConfigurationNodes(structureSchema, configuration, {});
    const structureNode = tree.children?.[0]!;

    expect(structureNode.children?.length).toBe(2);
    expect(structureNode.children?.[0].data.title).toBe('someField1');
    expect(structureNode.children?.[1].data.title).toBe('someField2');
  });

  test('root object with only patternProperties: children come from configuration keys', () => {
    const schema: SchemaDefinition = {
      type: 'object',
      readOnly: false,
      additionalProperties: false,
      properties: {},
      patternProperties: {
        '^[a-z]+$': { title: 'lowerKey', type: 'string', readOnly: false },
      },
    };
    const data: JSONObject = { ab: 'v1', cd: 'v2' };
    const tree = buildConfigurationNodes(schema, data, {});
    expect(tree.children?.length).toBe(2);
    expect(tree.children?.map((c) => c.key).sort()).toEqual(['/ab', '/cd']);
  });
});

describe('map node tests', () => {
  test('map', () => {
    const tree = buildConfigurationNodes(mapSchema, {}, {});
    const treeView = buildConfigurationTree(tree, emptyFilter);
    const mapNode = treeView.children?.[0]!;
    const mapNodeData = mapNode.data as ConfigurationObject;

    expect(mapNodeData.objectType).toBe('map');
    expect(mapNodeData.isReadonly).toBe(false);
    expect(mapNodeData.isNullable).toBe(false);
    expect(mapNodeData.isCleanable).toBe(false);
    expect(mapNode.children?.length).toBe(1);
    expect(mapNode.children?.[0].data.type).toBe('addField');
  });

  test('nullable', () => {
    const tree = buildConfigurationNodes(nullableMapSchema, {}, {});
    const viewTree = buildConfigurationTree(tree, emptyFilter);
    const mapNode = viewTree.children?.[0]!;
    const mapNodeData = mapNode.data as ConfigurationObject;

    expect(mapNodeData.isNullable).toBe(true);
    expect(mapNodeData.isCleanable).toBe(true);
    expect(mapNodeData.fieldSchema.type === 'object');

    const addPropertyButtonNode = mapNode.children?.[0]!;

    expect(addPropertyButtonNode.data.type).toBe('addField');
  });

  test('map with data', () => {
    const config = { map: { someField1: 'someField1Value', someField2: 'someField2Value' } };
    const tree = buildConfigurationNodes(mapSchema, config, {});
    const treeView = buildConfigurationTree(tree, emptyFilter);
    const mapNode = treeView.children?.[0]!;
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
    const tree = buildConfigurationNodes(mapSchemaWithPredefinedData, config, {});
    const treeView = buildConfigurationTree(tree, emptyFilter);
    const mapNode = treeView.children?.[0]!;
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
    const tree = buildConfigurationNodes(readonlyMapSchema, config, {});
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
    const tree = buildConfigurationNodes(listSchema, {}, {});
    const arrayNode = tree.children?.[0]!;
    const arrayNodeData = arrayNode.data as ConfigurationArray;

    expect(arrayNodeData.type).toBe('array');
    expect(arrayNodeData.isNullable).toBe(false);
    expect(arrayNodeData.isCleanable).toBe(false);
  });

  test('nullable array', () => {
    const tree = buildConfigurationNodes(nullableListSchema, {}, {});
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
    const tree = buildConfigurationNodes(listSchemaWithTitle, configuration, {});
    const arrayNodeWithTitle = tree.children?.[0]!;
    const item1NodeWithTitle = arrayNodeWithTitle.children?.[0]!;

    expect(arrayNodeWithTitle.data.title).toBe('Strings');
    expect(item1NodeWithTitle.data.title).toBe('Strings [0]');

    const tree2 = buildConfigurationNodes(listSchema, configuration, {});
    const arrayNodeWithDefaultTitle = tree2.children?.[0]!;
    const item1NodeWithDefaultTitle = arrayNodeWithDefaultTitle.children?.[0]!;

    expect(arrayNodeWithDefaultTitle.data.title).toBe('list');
    expect(item1NodeWithDefaultTitle.data.title).toBe('list [0]');
  });

  test('empty array', () => {
    const tree = buildConfigurationNodes(listSchema, {}, {});
    const treeView = buildConfigurationTree(tree, emptyFilter);
    const arrayNode = treeView.children?.[0]!;

    expect(arrayNode.children?.length).toBe(1);
    expect(arrayNode.children?.[0].data.type).toBe('addArrayItem');
  });

  test('array with data', () => {
    const config = {
      list: ['value1', 'value2'],
    };
    const tree = buildConfigurationNodes(listSchema, config, {});
    const treeView = buildConfigurationTree(tree, emptyFilter);
    const arrayNode = treeView.children?.[0]!;
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
    const tree = buildConfigurationNodes(readonlyListSchema, config, {});
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
    const tree = buildConfigurationNodes(fieldSchema, {}, {});
    const fieldNode = tree.children?.[0]!;
    const fieldNodeData = fieldNode.data as ConfigurationField;

    expect(fieldNode.children).toBe(undefined);
    expect(fieldNodeData.isDeletable).toBe(false);
    expect(fieldNodeData.isCleanable).toBe(false);
  });

  test('nullable field', () => {
    const tree = buildConfigurationNodes(nullableFieldSchema, {}, {});
    const fieldNode = tree.children?.[0]!;
    const fieldNodeData = fieldNode.data as ConfigurationField;

    expect(fieldNodeData.isNullable).toBe(true);
    expect(fieldNodeData.isCleanable).toBe(true);
    expect(fieldNodeData.fieldSchema.type === 'string');
  });

  test('title', () => {
    const tree = buildConfigurationNodes(fieldSchemaWithTitle, {}, {});
    const fieldNodeWithDefinedTitle = tree.children?.[0]!;

    expect(fieldNodeWithDefinedTitle.data.title).toBe('Field title');

    const tree2 = buildConfigurationNodes(fieldSchema, {}, {});
    const fieldNodeWithDefaultTitle = tree2.children?.[0]!;

    expect(fieldNodeWithDefaultTitle.data.title).toBe('someField1');
  });

  test('readonly field', () => {
    const tree = buildConfigurationNodes(readonlyFieldSchema, {}, {});
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

    const { isValid, configurationErrors } = validate(clusterConfigurationSchema, configuration, attributes);
    expect(isValid).toBe(false);
    expect(Object.keys(configurationErrors).length).not.toBe(0);
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

    const { isValid, configurationErrors } = validate(validateInactiveGroupSchema, configuration, attributes);
    expect(isValid).toBe(false);
    expect(Object.keys(configurationErrors).length === 2);
    expect(configurationErrors['/']).toBe(true);
    expect(configurationErrors['/structure_2']).toBe(true);
    expect(configurationErrors['/structure_2/someField1']).not.toBe(true);
    expect(typeof configurationErrors['/structure_2/someField1']).toBe('object');

    const fieldErrors = configurationErrors['/structure_2/someField1'];
    expect((fieldErrors as FieldErrors).messages).not.toStrictEqual({ required: 'must be string' });
  });

  test('fills parent paths (via service mapping)', () => {
    const rawErrors = [
      {
        instancePath: '/config/cluster/clusterName',
        parentSchema: {} as SchemaDefinition,
        data: {},
        keyword: 'type',
        message: 'x',
        params: {},
      },
    ];

    const { configurationErrors } = jsonSchemaValidationService.mapRawErrorsToConfigurationErrors('ajv', rawErrors, {});

    const expected: ConfigurationErrors = {
      '/': true,
      '/config': true,
      '/config/cluster': true,
      '/config/cluster/clusterName': expect.anything(),
    };

    expect(configurationErrors).toMatchObject(expected);
  });

  test('required validation', () => {
    const attributes = {};

    const configuration = {
      cluster_config: {
        cluster: {
          // ^-- must be an error
          // cluster_name: 'name', <-- required field
          shard: [],
        },
        auth: {
          token: 'test',
          expire: 10,
        },
      },
    };

    const { isValid, configurationErrors } = validate(clusterConfigurationSchema, configuration, attributes);
    expect(isValid).toBe(false);
    expect(configurationErrors['/cluster_config']).toBe(true);
    expect(configurationErrors['/cluster_config/cluster']).not.toBe(undefined);
    expect(configurationErrors['/cluster_config/cluster/cluster_name']).not.toBe(undefined);
  });

  test('validate nested props errors', () => {
    const attributes = {};
    const configuration = { list: [1] };

    const { isValid, configurationErrors } = validate(validateNestedErrorsSchema, configuration, attributes);
    expect(isValid).toBe(false);

    expect(typeof configurationErrors['/list']).toBe('object');
    expect((configurationErrors['/list'] as FieldErrors).messages[nestedPropsErrorKeyword]).toBe(
      nestedPropsErrorMessage,
    );
    expect(getErrorsForTreeRow(configurationErrors, '/list')).toBeUndefined();
    const leafKey = Object.keys(configurationErrors).find(
      (k) => k.startsWith('/list/') && typeof configurationErrors[k] === 'object',
    );
    expect(leafKey).toBeDefined();
    expect(getErrorsForTreeRow(configurationErrors, leafKey!)).toBeDefined();
  });

  test('validate configuration schema: errors on expected paths with correct structure', () => {
    const attributes: Record<string, { isActive: boolean }> = {};
    const configuration = configurationValidationData as JSONObject;

    const { isValid, configurationErrors } = validate(
      configurationValidationSchema as SchemaDefinition,
      configuration,
      attributes,
    );

    expect(isValid).toBe(false);
    expect(Object.keys(configurationErrors).length).toBeGreaterThan(0);

    expect(
      configurationErrors['/'] === true ||
        (typeof configurationErrors['/'] === 'object' && configurationErrors['/'] !== null),
    ).toBe(true);
    expect(
      configurationErrors['/my_group_with_required_not_default_parameters'] === true ||
        (typeof configurationErrors['/my_group_with_required_not_default_parameters'] === 'object' &&
          configurationErrors['/my_group_with_required_not_default_parameters'] !== null),
    ).toBe(true);
    expect(
      configurationErrors['/my_activatable_group'] === true ||
        (typeof configurationErrors['/my_activatable_group'] === 'object' &&
          configurationErrors['/my_activatable_group'] !== null),
    ).toBe(true);

    const expectFieldError = (path: string, expectedKeyword: string) => {
      const err = configurationErrors[path];
      expect(err).not.toBe(undefined);
      expect(err).not.toBe(true);
      const fieldErr = err as FieldErrors;
      expect(fieldErr.schema).toBeDefined();
      expect(fieldErr.messages).toBeDefined();
      expect(Object.keys(fieldErr.messages)).toContain(expectedKeyword);
    };

    expectFieldError('/my_password', 'type');
    expectFieldError('/my_list_variant', 'enum');

    const groupPath = '/my_group_with_required_not_default_parameters';
    const requiredFields = [
      'my_boolean',
      'my_float',
      'my_integer',
      'my_list',
      'my_map',
      'my_string',
      'my_text',
      'my_json',
      'my_file',
      'my_password',
      'secrettext',
      'my_list_variant',
      'my_inline_variant_not_strict',
      'my_inline_variant_strict',
    ];
    const enumOnlyFields = new Set(['my_list_variant', 'my_inline_variant_strict']);
    for (const field of requiredFields) {
      const path = `${groupPath}/${field}`;
      const keyword = enumOnlyFields.has(field) ? 'enum' : 'type';
      expectFieldError(path, keyword);
    }

    // my_activatable_group: my_password null → type
    expectFieldError('/my_activatable_group/my_password', 'type');
  });
});

describe('filter', () => {
  test('find something', () => {
    const tree = buildConfigurationNodes(clusterConfigurationSchema, clusterConfiguration, {});
    const filteredTree = buildConfigurationTree(tree, { title: 'Name', showAdvanced: false, showInvisible: false });
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

  test('find in parent', () => {
    const configuration = {
      structure: {
        someField1: 'value1',
        someField2: 'value2',
      },
    };
    const tree = buildConfigurationNodes(structureSchema, configuration, {});
    // eslint-disable-next-line spellcheck/spell-checker
    const filteredTree = buildConfigurationTree(tree, { title: 'truct', showAdvanced: false, showInvisible: false });
    const structureNode = filteredTree.children?.[0]!;

    expect(structureNode.children?.length).toBe(2);
    expect(structureNode.children?.[0].data.title).toBe('someField1');
    expect(structureNode.children?.[1].data.title).toBe('someField2');
  });

  test('not find in parent', () => {
    const configuration = {
      structure: {
        someField1: 'value1',
        someField2: 'value2',
      },
    };
    const tree = buildConfigurationNodes(structureSchema, configuration, {});
    // eslint-disable-next-line spellcheck/spell-checker
    const filteredTree = buildConfigurationTree(tree, { title: 'blabla', showAdvanced: false, showInvisible: false });
    const structureNode = filteredTree.children?.[0]!;

    expect(structureNode).toBe(undefined);
  });

  test('find in children', () => {
    const configuration = {
      structure: {
        someField1: 'value1',
        someField2: 'value2',
      },
    };
    const tree = buildConfigurationNodes(structureSchema, configuration, {});
    // eslint-disable-next-line spellcheck/spell-checker
    const filteredTree = buildConfigurationTree(tree, { title: 'ld1', showAdvanced: false, showInvisible: false });
    const structureNode = filteredTree.children?.[0]!;

    expect(structureNode.children?.length).toBe(1);
    expect(structureNode.children?.[0].data.title).toBe('someField1');
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

    const tree = buildConfigurationNodes(clusterConfigurationSchema, clusterConfiguration, attributes);

    const clusterConfigNode = tree.children?.[0]!;
    expect(clusterConfigNode.data.fieldAttributes).toStrictEqual(clusterConfigAttributes);

    const clusterNode = clusterConfigNode.children?.[0]!;
    expect(clusterNode.data.fieldAttributes).toStrictEqual(clusterAttributes);

    const authNode = clusterConfigNode.children?.[1]!;
    expect(authNode.data.fieldAttributes).toStrictEqual(authAttributes);
  });
});

describe('selection groups', () => {
  test('build discriminator field', () => {
    const tree = buildConfigurationNodes(selectableObjectSchema, selectableObjectConfig, {});
    const clusterConfigNode = tree.children?.[0]!;
    expect(clusterConfigNode.data.type).toStrictEqual('selectableObject');
    expect(clusterConfigNode.children?.[0].key.endsWith(discriminatorFieldName)).toBeTruthy();
    expect(clusterConfigNode.children?.[0].data.type).toStrictEqual('field');
  });
});

describe('getErrorsForTreeRow', () => {
  test('hides parent FieldErrors when a descendant has FieldErrors', () => {
    const errors: ConfigurationErrors = {
      '/g': { schema: {} as SchemaDefinition, value: {}, messages: { oneOf: 'x' } },
      '/g/x': { schema: {} as SchemaDefinition, value: null, messages: { required: 'required' } },
    };
    expect(getErrorsForTreeRow(errors, '/g')).toBeUndefined();
    expect(getErrorsForTreeRow(errors, '/g/x')).toBeDefined();
  });

  test('keeps FieldErrors when no object-shaped descendant', () => {
    const errors: ConfigurationErrors = {
      '/g': { schema: {} as SchemaDefinition, value: {}, messages: { type: 'x' } },
      '/g/x': true,
    };
    expect(getErrorsForTreeRow(errors, '/g')).toBeDefined();
  });
});

describe('getConfigurationErrors root instancePath', () => {
  test('object-level keywords (minProperties) attach to / so the root row shows FieldErrors', () => {
    const schema: SchemaDefinition = {
      type: 'object',
      readOnly: false,
      additionalProperties: false,
      minProperties: 2,
      maxProperties: 2,
      properties: {
        a: { title: 'a', type: 'string', readOnly: false },
        b: { title: 'b', type: 'string', readOnly: false },
        c: { title: 'c', type: 'string', readOnly: false },
      },
    };
    const data: JSONObject = { a: 'only' };
    const raw = validateJsonSchema(schema, data);
    expect(raw).not.toBe(null);
    const { configurationErrors } = jsonSchemaValidationService.mapRawErrorsToConfigurationErrors('ajv', raw, {});
    expect(typeof configurationErrors['/']).toBe('object');
    expect(getErrorsForTreeRow(configurationErrors, '/')).toBeDefined();
  });

  test('required leaf path does not become //x when instancePath is "/"', () => {
    // AJV normally uses "" for root, but we also generate synthetic root errors with "/" (e.g. schema compilation errors).
    // When we attach a missing-property marker for UI, we must produce "/<prop>", not "//<prop>".
    const errors = [
      {
        instancePath: '/',
        parentSchema: { type: 'object', required: ['x'] } as unknown as SchemaDefinition,
        data: {} as JSONObject,
        keyword: 'required',
        message: "must have required property 'x'",
        params: { missingProperty: 'x' },
      },
    ] as unknown as ReturnType<typeof validateJsonSchema>;

    const { configurationErrors } = jsonSchemaValidationService.mapRawErrorsToConfigurationErrors('ajv', errors, {});
    expect(configurationErrors['/x']).toBeDefined();
    expect(configurationErrors['//x']).toBeUndefined();
  });
});

describe('getConfigurationErrors + discriminated oneOf', () => {
  test('leaf path exists for missing required inside selected branch', () => {
    const data: JSONObject = {
      selectable_no_default_required: { _selection: 'a', a: {} },
    };
    const raw = validateJsonSchema(selectableObjectSchema, data);
    expect(raw).not.toBe(null);
    const { configurationErrors } = jsonSchemaValidationService.mapRawErrorsToConfigurationErrors('ajv', raw, {});
    expect(configurationErrors['/selectable_no_default_required/a/plain']).toBeDefined();
  });
});

describe('getOneOfSchemaDefaults', () => {
  const selectableFieldSchema = selectableObjectSchema.properties!.selectable_no_default_required;

  test('returns empty object when oneOf is absent', () => {
    expect(getOneOfSchemaDefaults({ type: 'object', properties: {} } as SchemaDefinition)).toEqual({});
  });

  test('builds a default object per discriminator value', () => {
    const defaults = getOneOfSchemaDefaults(selectableFieldSchema as SchemaDefinition);

    expect(Object.keys(defaults).sort()).toEqual(['a', 'b']);

    const a = defaults.a as JSONObject;
    const b = defaults.b as JSONObject;

    expect(a[discriminatorFieldName]).toBe('a');
    expect(b[discriminatorFieldName]).toBe('b');
    expect(a.a).toEqual({ plain: 2 });
    expect(b.b).toEqual({ plain: 2 });
    expect(a.b).toBeUndefined();
    expect(b.a).toBeUndefined();
  });

  test('parent union default does not leak into other branches', () => {
    const defaults = getOneOfSchemaDefaults(selectableObjectFieldSchemaWithUnionDefault);

    const a = defaults.a as JSONObject;
    const b = defaults.b as JSONObject;

    expect(a[discriminatorFieldName]).toBe('a');
    expect(b[discriminatorFieldName]).toBe('b');
    expect(b.a).toBeUndefined();
    expect(b.b).toEqual({ plain: 2 });
  });
});

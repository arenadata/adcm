import type {
  ConfigurationData,
  ConfigurationSchema,
  SchemaDefinition,
  SchemaTypeName,
  ConfigurationErrors,
  ConfigurationAttributes,
  FieldAttributes,
  FieldErrors,
} from '@models/adcm';
import type { JSONValue, JSONObject, JSONPrimitive } from '@models/json';
import type {
  ConfigurationObject,
  ConfigurationNode,
  ConfigurationTreeFilter,
  ConfigurationNodePath,
  ConfigurationArray,
  ConfigurationNodeView,
  ConfigurationTreeState,
  NodesDictionary,
  ConfigurationSelectableObject,
  ConfigurationField,
} from '../ConfigurationEditor.types';
import {
  DEFAULT_JSON_SCHEMA_ENGINE,
  jsonSchemaValidationService,
  type JsonSchemaEngineId,
} from '@utils/jsonSchema/JsonSchemaValidationService';
import { discriminatorFieldName, primitiveFieldTypes, rootNodeKey, rootNodeTitle } from './ConfigurationTree.constants';
import { isObject } from '@utils/objectUtils';

const getIndex = (nodeArr?: ConfigurationNode[]) => (nodeArr && nodeArr.length > 0 ? nodeArr.at(-1)!.index + 1 : 0);

export const validate = (
  schema: SchemaDefinition,
  configuration: JSONObject,
  attributes: ConfigurationAttributes,
  engine: JsonSchemaEngineId = DEFAULT_JSON_SCHEMA_ENGINE,
) => {
  return jsonSchemaValidationService.validate(engine, schema, configuration, attributes);
};

/** Path `p` is a strict descendant of `ancestorKey` in the config tree (`/a` → `/a/b`, not `/ab`). */
function isStrictDescendantErrorPath(ancestorKey: string, path: string): boolean {
  if (ancestorKey === rootNodeKey) {
    return path !== rootNodeKey && path.length > 1 && path.startsWith('/');
  }
  return path.startsWith(`${ancestorKey}/`);
}

/**
 * FieldErrors for row UI (MarkerIcon). Omit when any strict descendant already has its own FieldErrors;
 * parent may still be `true` in the map for {@link CollapseNode} styling.
 */
export function getErrorsForTreeRow(
  configurationErrors: ConfigurationErrors,
  nodeKey: string,
): FieldErrors | undefined {
  const entry = configurationErrors[nodeKey];
  if (typeof entry !== 'object') return undefined;

  for (const path of Object.keys(configurationErrors)) {
    if (path === nodeKey) continue;
    if (typeof configurationErrors[path] !== 'object') continue;
    if (isStrictDescendantErrorPath(nodeKey, path)) return undefined;
  }

  return entry as FieldErrors;
}

export const getTitle = (keyName: string, fieldSchema: SchemaDefinition) =>
  fieldSchema.title?.length ? fieldSchema.title : keyName;

export const getDefaultValue = (keyName: string, node: SchemaDefinition, parentNode: SchemaDefinition) => {
  const parentNodeDefault = parentNode.default?.[keyName as keyof typeof parentNode.default];
  const nodeDefault = node.default;

  return nodeDefault ?? parentNodeDefault;
};

export const resolveFieldDefaultValue = (
  field: Pick<ConfigurationField, 'defaultValue' | 'fieldSchema'>,
): JSONPrimitive => {
  if (field.defaultValue !== undefined) {
    return field.defaultValue;
  }

  if (field.fieldSchema.default !== undefined) {
    return field.fieldSchema.default as JSONPrimitive;
  }

  return undefined;
};

export const hasFieldDefaultValue = (field: Pick<ConfigurationField, 'defaultValue' | 'fieldSchema'>): boolean =>
  resolveFieldDefaultValue(field) !== undefined;

const getDefaultFieldSchema = (parentFieldSchema: SchemaDefinition | null): SchemaDefinition => {
  const fieldSchema: SchemaDefinition = {
    type: 'string',
    readOnly: false,
  };

  if (parentFieldSchema?.adcmMeta?.isSecret) {
    if (fieldSchema.adcmMeta === undefined) {
      fieldSchema.adcmMeta = {};
    }
    fieldSchema.adcmMeta.isSecret = true;
  }

  if (parentFieldSchema?.readOnly) {
    fieldSchema.readOnly = true;
  }

  return fieldSchema;
};

/**
 * Resolve per-key schema for map-like objects.
 *
 * We support keys that are present in data but absent in `properties`:
 * - prefer explicit `properties[key]`
 * - else match the first `patternProperties` regex (ECMA-262)
 * - else fall back to a primitive schema so the UI has a renderable control
 */
const resolvePropertySchemaForObjectKey = (
  parentFieldSchema: SchemaDefinition,
  propertyKey: string,
): SchemaDefinition => {
  const explicit = parentFieldSchema.properties?.[propertyKey];
  if (explicit) return explicit;

  const patternMap = parentFieldSchema.patternProperties;
  if (patternMap && typeof patternMap === 'object') {
    for (const [pattern, subSchema] of Object.entries(patternMap)) {
      if (!subSchema || typeof subSchema !== 'object') continue;
      try {
        const re = new RegExp(pattern);
        if (re.test(propertyKey)) {
          return subSchema as SchemaDefinition;
        }
      } catch {
        // ignore invalid regex in schema
      }
    }
  }

  return getDefaultFieldSchema(parentFieldSchema);
};

const isRootReadOnlyLocked = (parentNode: ConfigurationNode): boolean => {
  let node: ConfigurationNode = parentNode;

  while (node.key !== rootNodeKey) {
    node = node.data.parentNode;
  }

  // Root `isReadonly` is set from ConfigurationTree `isReadOnly` (wizard non-current step).
  return node.data.isReadonly;
};

const getIsReadonly = (
  fieldSchema: SchemaDefinition,
  fieldAttributes: FieldAttributes,
  parentNode: ConfigurationNode,
) => {
  const parentNodeData = parentNode.data as ConfigurationObject | ConfigurationArray;

  if (isRootReadOnlyLocked(parentNode)) {
    return true;
  }

  const isArrayItem = parentNodeData.fieldSchema.type === 'array';
  const isMapProperty = parentNode.data.type === 'object' && parentNode.data.objectType === 'map';

  if ((isArrayItem || isMapProperty) && parentNodeData.isReadonly) {
    return true;
  }

  if (fieldAttributes?.isSynchronized !== undefined) {
    return fieldAttributes.isSynchronized;
  }

  if (parentNodeData.fieldAttributes?.isSynchronized !== undefined) {
    return parentNodeData.fieldAttributes?.isSynchronized;
  }

  // selection_group: writable is per-field; do not inherit selection group isReadonly to subs.
  if (parentNode.data.type === 'selectableObject') {
    return Boolean(fieldSchema.readOnly);
  }

  return fieldSchema.readOnly || parentNodeData.isReadonly;
};

const getNodeProps = (
  fieldName: string,
  fieldSchema: SchemaDefinition,
  isNullable: boolean,
  fieldAttributes: FieldAttributes,
  parentNode: ConfigurationNode,
) => {
  const parentNodeData = parentNode.data;

  const isArrayItem = parentNodeData.fieldSchema.type === 'array';
  const title = isArrayItem ? `${parentNodeData.title} [${fieldName}]` : getTitle(fieldName, fieldSchema);

  let isRequiredField = false;

  if (parentNodeData.type === 'object') {
    const requiredFields = parentNodeData.fieldSchema.required ?? [];
    isRequiredField = requiredFields.includes(fieldName);
  } else if (parentNodeData.type === 'selectableObject') {
    const requiredFields = parentNodeData.selectedFieldSchema?.required ?? [];
    isRequiredField = requiredFields.includes(fieldName);
  }

  const isReadonly = getIsReadonly(fieldSchema, fieldAttributes, parentNode);
  const isCleanable = !isReadonly && isNullable;
  const isDeletable = !isReadonly && (!isRequiredField || isArrayItem);
  const isDraggable = !isReadonly && isArrayItem;

  return {
    title,
    isArrayItem,
    isRequiredField,
    isReadonly,
    isCleanable,
    isDeletable,
    isDraggable,
  };
};

export const buildConfigurationNodes = (
  schema: ConfigurationSchema,
  configuration: ConfigurationData,
  attributes: ConfigurationAttributes,
  isReadOnly?: boolean,
  engine: JsonSchemaEngineId = DEFAULT_JSON_SCHEMA_ENGINE,
): ConfigurationNode => {
  const rootNode = buildRootNode(schema, configuration, attributes, isReadOnly, engine);
  return rootNode;
};

export function* iterateConfigurationNodes(node: ConfigurationNode): Iterable<ConfigurationNode> {
  yield node;

  if (node.children) {
    for (const child of node.children) {
      yield* iterateConfigurationNodes(child);
    }
  }
}

export const buildNodeDictionary = (tree: ConfigurationNode) => {
  const dictionary: NodesDictionary = {};

  for (const node of iterateConfigurationNodes(tree)) {
    dictionary[node.key] = node;
  }

  return dictionary;
};

const buildRootNode = (
  schema: ConfigurationSchema,
  configuration: ConfigurationData,
  attributes: ConfigurationAttributes,
  isReadOnly = false,
  engine: JsonSchemaEngineId = DEFAULT_JSON_SCHEMA_ENGINE,
): ConfigurationNode => {
  const { fieldSchema } = determineFieldSchema(schema);
  const rootNode: ConfigurationNode = {
    key: rootNodeKey,
    index: 0,
    data: {
      title: getTitle(rootNodeTitle, fieldSchema),
      type: 'object',
      path: [],
      parentNode: {} as ConfigurationNode,
      fieldSchema,
      isNullable: false,
      isDeletable: false,
      isReadonly: isReadOnly,
      isCleanable: false,
      isDraggable: false,
      objectType: 'structure',
      value: configuration,
    },
  };

  const children: ConfigurationNode[] = [];
  const props = fieldSchema.properties ?? {};
  // We render both schema-defined properties and extra keys present in data (maps / patternProperties).
  const addedKeys = new Set<string>();

  Object.entries(props).forEach(([key, childSchema], index) => {
    if (childSchema === undefined) {
      return;
    }
    children.push(buildNode(index, key, [key], rootNode, childSchema, configuration[key], attributes, engine));
    addedKeys.add(key);
  });

  let nextIndex = children.length;
  for (const key of Object.keys(configuration)) {
    if (addedKeys.has(key)) continue;
    const childSchema = resolvePropertySchemaForObjectKey(fieldSchema, key);
    children.push(buildNode(nextIndex, key, [key], rootNode, childSchema, configuration[key], attributes, engine));
    addedKeys.add(key);
    nextIndex++;
  }

  rootNode.children = children.length ? children : undefined;

  return rootNode;
};

const buildNode = (
  index: number,
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SchemaDefinition,
  fieldValue: JSONValue,
  attributes: ConfigurationAttributes,
  engine: JsonSchemaEngineId = DEFAULT_JSON_SCHEMA_ENGINE,
): ConfigurationNode => {
  const { fieldSchema: singleFieldSchema, isNullable } = determineFieldSchema(fieldSchema);

  if (singleFieldSchema.type === 'object' && singleFieldSchema.discriminator === undefined) {
    return buildObjectNode(
      index,
      fieldName,
      path,
      parentNode,
      singleFieldSchema,
      isNullable,
      fieldValue,
      attributes,
      engine,
    );
  }

  if (singleFieldSchema.type === 'object' && singleFieldSchema.discriminator !== undefined) {
    return buildSelectableObjectNode(
      index,
      fieldName,
      path,
      parentNode,
      singleFieldSchema,
      isNullable,
      fieldValue,
      attributes,
      engine,
    );
  }

  if (singleFieldSchema.type === 'array') {
    return buildArrayNode(
      index,
      fieldName,
      path,
      parentNode,
      singleFieldSchema,
      isNullable,
      fieldValue,
      attributes,
      engine,
    );
  }

  if (primitiveFieldTypes.has(singleFieldSchema.type as string)) {
    return buildFieldNode(index, fieldName, path, parentNode, singleFieldSchema, isNullable, fieldValue, attributes);
  }

  if (singleFieldSchema.type === undefined && singleFieldSchema.enum) {
    return buildFieldNode(index, fieldName, path, parentNode, singleFieldSchema, isNullable, fieldValue, attributes);
  }

  if (fieldName === discriminatorFieldName) {
    return buildFieldNode(index, fieldName, path, parentNode, singleFieldSchema, isNullable, fieldValue, attributes);
  }

  /*
   * `items: {}` (empty schema) allows any JSON value; the editor needs a concrete control.
   * Infer a primitive type from the runtime value instead of falling through to UNKNOWN FIELD.
   * validation.arrays.contains_basic / validation.arrays.contains_minContains_2/ validation.arrays.contains_maxContains_1
   */
  const isEmptySchemaWithoutType =
    singleFieldSchema.type === undefined &&
    singleFieldSchema.enum === undefined &&
    singleFieldSchema.oneOf === undefined;

  const hasRuntimeValue = fieldValue !== null && fieldValue !== undefined;

  if (isEmptySchemaWithoutType && hasRuntimeValue) {
    const valueType = typeof fieldValue;
    const isSupportedPrimitive = valueType === 'string' || valueType === 'number' || valueType === 'boolean';

    if (isSupportedPrimitive) {
      let inferredType: SchemaTypeName;

      if (valueType === 'number') {
        const asNumber = fieldValue as number;
        inferredType = Number.isInteger(asNumber) ? 'integer' : 'number';
      } else {
        inferredType = valueType as SchemaTypeName;
      }

      // `items: {}` (empty schema) allows any JSON value; infer a concrete primitive type from runtime value
      // so we can render a usable control instead of an UNKNOWN field.
      const inferredSchema: SchemaDefinition = {
        ...singleFieldSchema,
        type: inferredType,
        title: singleFieldSchema.title ?? `Item #${fieldName}`,
      };

      return buildFieldNode(index, fieldName, path, parentNode, inferredSchema, isNullable, fieldValue, attributes);
    }
  }

  return buildUnknownNode(index, fieldName, path, parentNode, singleFieldSchema);
};

const buildObjectNode = (
  index: number,
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SchemaDefinition,
  isNullable: boolean,
  fieldValue: JSONValue,
  attributes: ConfigurationAttributes,
  engine: JsonSchemaEngineId = DEFAULT_JSON_SCHEMA_ENGINE,
) => {
  const key = buildKey(path);
  const fieldAttributes = attributes[key];

  const { title, isReadonly, isCleanable, isDeletable, isDraggable } = getNodeProps(
    fieldName,
    fieldSchema,
    isNullable,
    fieldAttributes,
    parentNode,
  );

  const node: ConfigurationNode = {
    key,
    index,
    data: {
      title,
      type: 'object',
      path,
      fieldSchema,
      isNullable,
      parentNode,
      isCleanable,
      isDeletable,
      isReadonly,
      isDraggable,
      objectType: 'map',
      defaultValue: getDefaultValue(fieldName, fieldSchema, parentNode.data.fieldSchema) as JSONObject,
      value: fieldValue,
      fieldAttributes,
    },
  };

  const nodeData = node.data as ConfigurationObject;

  // Objects may be described via `patternProperties` without `properties`.
  if (fieldSchema === undefined) {
    const fullPath = [...path, fieldName];
    console.error(`schema for /${fullPath.join('/')} not found`);
  } else {
    if (!fieldSchema.additionalProperties) {
      nodeData.objectType = 'structure';
    }

    node.children = addObjectProperties(node, attributes, engine);
  }

  return node;
};

const buildSelectableObjectNode = (
  index: number,
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SchemaDefinition,
  isNullable: boolean,
  fieldValue: JSONValue,
  attributes: ConfigurationAttributes,
  engine: JsonSchemaEngineId = DEFAULT_JSON_SCHEMA_ENGINE,
) => {
  const key = buildKey(path);
  const fieldAttributes = attributes[key];

  const { title, isReadonly, isCleanable, isDeletable, isDraggable } = getNodeProps(
    fieldName,
    fieldSchema,
    isNullable,
    fieldAttributes,
    parentNode,
  );

  const node: ConfigurationNode = {
    key,
    index,
    data: {
      title,
      type: 'selectableObject',
      path,
      fieldSchema,
      selectedFieldSchema: determineSelectableFieldSchema(fieldSchema, fieldValue),
      oneOfSchemaDefaults: getOneOfSchemaDefaults(fieldSchema, engine),
      isNullable,
      parentNode,
      isCleanable,
      isDeletable,
      isReadonly,
      isDraggable,
      defaultValue: getDefaultValue(fieldName, fieldSchema, parentNode.data.fieldSchema) as JSONObject,
      value: fieldValue,
      fieldAttributes,
    },
  };

  if (fieldSchema === undefined) {
    const fullPath = [...path, fieldName];
    console.error(`schema for /${fullPath.join('/')} not found`);
  } else {
    node.children = addObjectProperties(node, attributes, engine);
  }

  return node;
};

const addObjectProperties = (
  node: ConfigurationNode,
  attributes: ConfigurationAttributes,
  engine: JsonSchemaEngineId,
) => {
  const configObject = node.data as ConfigurationObject | ConfigurationSelectableObject;
  const { value, path } = configObject;

  const fieldSchema = configObject.type === 'object' ? configObject.fieldSchema : configObject.selectedFieldSchema;

  // Guard: schema may declare object, but the runtime value can still be scalar/null/array.
  // Only treat plain objects as objects for children rendering.
  const objectValue =
    typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as JSONObject) : null;

  const children = [];

  if (fieldSchema && objectValue) {
    const addedFields = new Set<string>();
    const props = fieldSchema.properties ?? {};
    const propertyKeys = Object.keys(props);

    // add children from schema
    for (const [key, propName] of propertyKeys.entries()) {
      const childrenFieldSchema = props[propName];
      if (childrenFieldSchema === undefined) {
        continue;
      }

      const fieldPath = [...path, propName];
      const propertyValue = objectValue[propName] ?? null;

      children.push(buildNode(key, propName, fieldPath, node, childrenFieldSchema, propertyValue, attributes, engine));
      addedFields.add(propName);
    }

    // Add children from data (map-like objects / patternProperties keys not listed in `properties`).
    let index = children.length;
    for (const [key, propertyValue] of Object.entries(objectValue)) {
      if (!addedFields.has(key)) {
        const fieldPath = [...path, key];
        const childrenFieldSchema = resolvePropertySchemaForObjectKey(fieldSchema, key);

        children.push(buildNode(index, key, fieldPath, node, childrenFieldSchema, propertyValue, attributes, engine));
        addedFields.add(key);
        index++;
      }
    }
  }

  return children.length ? children : undefined;
};

const buildFieldNode = (
  index: number,
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SchemaDefinition,
  isNullable: boolean,
  fieldValue: JSONValue,
  attributes: ConfigurationAttributes,
) => {
  const key = buildKey(path);
  const fieldAttributes = attributes[key];

  const { title, isReadonly, isCleanable, isDeletable, isDraggable } = getNodeProps(
    fieldName,
    fieldSchema,
    isNullable,
    fieldAttributes,
    parentNode,
  );

  const node: ConfigurationNode = {
    key,
    index,
    data: {
      title,
      type: 'field',
      path,
      parentNode,
      fieldSchema,
      isNullable,
      defaultValue: getDefaultValue(fieldName, fieldSchema, parentNode.data.fieldSchema) as JSONPrimitive,
      value: fieldValue as JSONPrimitive,
      isCleanable,
      isDeletable,
      isReadonly,
      isDraggable,
      fieldAttributes,
    },
  };

  return node;
};

const buildAddEmptyObjectNode = (
  path: ConfigurationNodePath,
  fieldSchema: SchemaDefinition,
  parentNode: ConfigurationNode,
) => {
  const index = getIndex(parentNode.children);

  const node: ConfigurationNodeView = {
    key: buildKey([...path, 'addEmptyObjectButton']),
    index,
    data: {
      type: 'addEmptyObject',
      title: 'Set',
      path,
      parentNode,
      fieldSchema,
    },
  };

  return node;
};

const buildAddFieldNode = (path: ConfigurationNodePath, parentNode: ConfigurationNode) => {
  const fieldSchema: SchemaDefinition = getDefaultFieldSchema(parentNode.data.fieldSchema);
  const index = getIndex(parentNode.children);

  const node: ConfigurationNodeView = {
    key: buildKey([...path, 'addFieldButton']),
    index,
    data: {
      type: 'addField',
      title: 'Add property',
      path,
      parentNode,
      fieldSchema,
    },
  };

  return node;
};

const buildArrayNode = (
  index: number,
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SchemaDefinition,
  isNullable: boolean,
  fieldValue: JSONValue,
  attributes: ConfigurationAttributes,
  engine: JsonSchemaEngineId = DEFAULT_JSON_SCHEMA_ENGINE,
) => {
  const array = fieldValue as Array<JSONValue> | null;

  const key = buildKey(path);
  const fieldAttributes = attributes[key];

  const { title, isReadonly, isCleanable, isDeletable, isDraggable } = getNodeProps(
    fieldName,
    fieldSchema,
    isNullable,
    fieldAttributes,
    parentNode,
  );

  const node: ConfigurationNode = {
    key,
    index,
    data: {
      title,
      type: 'array',
      path,
      parentNode,
      fieldSchema,
      isNullable,
      isReadonly,
      isCleanable,
      isDeletable,
      isDraggable,
      defaultValue: getDefaultValue(fieldName, fieldSchema, parentNode.data.fieldSchema) as JSONPrimitive,
      value: array,
      fieldAttributes,
    },
  };

  /*
   * JSON Schema tuple arrays:
   * - `prefixItems` define per-index schemas
   * - `items` apply after `prefixItems`
   * - `items: false` forbids extra elements
   *
   * The UI must still render existing data elements even when forbidden, so we show them as "not allowed".
   */
  const prefixItemsSchemas = fieldSchema.prefixItems;
  const itemsSchema = fieldSchema.items;

  const getSchemaForIndex = (i: number): SchemaDefinition | undefined => {
    const schemaFromPrefix = prefixItemsSchemas?.[i];
    if (schemaFromPrefix) return schemaFromPrefix;
    if (itemsSchema === false) return undefined;
    return itemsSchema;
  };
  node.children = [];

  if (array) {
    for (let i = 0; i < array.length; i++) {
      const elementPath = [...path, i];
      const schemaForIndex = getSchemaForIndex(i);

      node.children.push(
        schemaForIndex
          ? buildNode(i, i.toString(), elementPath, node, schemaForIndex, array[i], attributes, engine)
          : buildUnknownNode(i, i.toString(), elementPath, node, {} as SchemaDefinition),
      );
    }
  }

  return node;
};

const buildAddArrayItemNode = (
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SchemaDefinition,
) => {
  const index = getIndex(parentNode.children);
  const node: ConfigurationNodeView = {
    key: buildKey([...path, 'addArrayItemButton']),
    index,
    data: {
      type: 'addArrayItem',
      title: 'Add property',
      path,
      parentNode,
      fieldSchema,
    },
  };

  return node;
};

const buildItemDropPlaceholderNode = (
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SchemaDefinition,
) => {
  const index = getIndex(parentNode.children);
  const node: ConfigurationNodeView = {
    key: buildKey([...path, 'itemDropPlaceholder']),
    index,
    data: {
      type: 'dropPlaceholder',
      title: '1',
      path,
      parentNode,
      fieldSchema,
    },
  };

  return node;
};

const buildUnknownNode = (
  index: number,
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SchemaDefinition,
) => {
  // Keep unknown nodes readable: include field name + schema type; allow overrides for special cases (e.g. "not allowed").
  const title =
    fieldSchema.title ??
    `UNKNOWN FIELD: ${fieldName}, TYPE: ${fieldSchema.type === undefined ? 'undefined' : String(fieldSchema.type)}`;
  const node: ConfigurationNode = {
    key: buildKey(path),
    index,
    data: {
      title,
      type: 'field',
      path,
      parentNode,
      fieldSchema,
      isNullable: false,
      value: 'some value',
      defaultValue: 'some default value',
      isCleanable: false,
      isDeletable: false,
      isReadonly: true,
      isDraggable: false,
    },
  };

  return node;
};

const buildKey = (path: ConfigurationNodePath) => `/${path.join('/')}`;

export const buildConfigurationTree = (
  rootNode: ConfigurationNode,
  filter: ConfigurationTreeFilter,
  treeState?: ConfigurationTreeState,
): ConfigurationNodeView => {
  if (rootNode.children) {
    const filteredChildren = [];
    for (const child of rootNode.children) {
      const childNodeView = buildConfigurationTreeRecursively(child, filter, false, treeState);
      if (childNodeView) {
        filteredChildren.push(childNodeView);
      }
    }

    (rootNode as ConfigurationNodeView).children = filteredChildren;
  }

  return rootNode;
};

const buildConfigurationTreeRecursively = (
  node: ConfigurationNode,
  filter: ConfigurationTreeFilter,
  foundInParent: boolean,
  treeState?: ConfigurationTreeState,
): ConfigurationNodeView | undefined => {
  const treeNode = node as ConfigurationNodeView;

  const isVisible =
    (filter.showInvisible ? true : !treeNode.data.fieldSchema.adcmMeta?.isInvisible) &&
    (filter.showAdvanced ? true : !treeNode.data.fieldSchema.adcmMeta?.isAdvanced);

  if (!isVisible) {
    return undefined;
  }

  if (node.data.path.at(-1) === discriminatorFieldName) {
    return undefined;
  }

  const foundInTitle = treeNode.data.title.toLowerCase().includes(filter.title.toLowerCase());

  const filteredChildren = [];
  if (node.children) {
    for (const child of node.children) {
      const childNodeView = buildConfigurationTreeRecursively(child, filter, foundInTitle, treeState);
      if (childNodeView) {
        filteredChildren.push(childNodeView);
      }
    }
  }

  treeNode.children = filteredChildren.length ? filteredChildren : undefined;

  const foundInChildren = Boolean(treeNode.children?.length);
  if (!(foundInParent || foundInTitle || foundInChildren)) {
    return undefined;
  }

  const nodeData = node.data;
  if (nodeData.type === 'object' && !nodeData.isReadonly) {
    let addNode: ConfigurationNodeView | undefined = undefined;
    if (nodeData.objectType === 'map') {
      addNode = buildAddFieldNode(nodeData.path, node);
    }
    if (nodeData.objectType === 'structure' && nodeData.value === null) {
      addNode = buildAddEmptyObjectNode(nodeData.path, nodeData.fieldSchema, nodeData.parentNode);
    }

    if (addNode) {
      if (treeNode.children === undefined) {
        treeNode.children = [];
      }
      treeNode.children.push(addNode);
    }
  }

  if (nodeData.type === 'array' && !nodeData.isReadonly) {
    // `ConfigurationEditor` array UI needs a concrete schema for:
    // - building "Add property" button
    // - building drop placeholder nodes on drag
    //
    // For tuple arrays (`prefixItems`) with `additionalItems` / `unevaluatedItems`, there might be no `items`.
    // In that case we must not try to build add/drop nodes with `undefined` schema (it crashes in `getNodeClassName`).
    const nodeFieldSchema = nodeData.fieldSchema;

    const asArrayItemSchema = (s: SchemaDefinition | false | undefined): SchemaDefinition | undefined => {
      if (s === undefined || s === false) return undefined;
      return s;
    };

    const itemsSchema =
      asArrayItemSchema(nodeFieldSchema.items) ??
      asArrayItemSchema(nodeFieldSchema.additionalItems) ??
      asArrayItemSchema(nodeFieldSchema.unevaluatedItems);

    if (treeNode.children === undefined) {
      treeNode.children = [];
    }

    // Tuple-only arrays can have no `items` at all; in that case, do not create add/drop UI (would crash on undefined schema).
    const canBuildAddOrDropNodes = itemsSchema !== undefined;

    // add drop placeholders on drag
    if (canBuildAddOrDropNodes && treeState?.dragNode?.data && treeNode.children.length) {
      const isDragItemInArray = treeState.dragNode.data.parentNode.key === node.key;
      if (isDragItemInArray) {
        const childrenWithDropPlaceholders: ConfigurationNodeView[] = [];

        for (let i = 0; i < treeNode.children.length; i++) {
          const dragNodeIndex = Number(treeState.dragNode.data.path.at(-1));

          // add drop placeholder at first, but skip when node[0] is draggable node
          if (i === 0 && dragNodeIndex !== 0) {
            const dropPlaceholderPath = [...node.data.path, 0];
            childrenWithDropPlaceholders.push(buildItemDropPlaceholderNode(dropPlaceholderPath, node, itemsSchema));
          }

          childrenWithDropPlaceholders.push(treeNode.children[i]);

          // add drop placeholder after node, but skip when node is draggable node
          if (dragNodeIndex !== i && dragNodeIndex !== i + 1) {
            const placeholderIndex = i < dragNodeIndex ? i + 1 : i;
            const dropPlaceholderPath = [...node.data.path, placeholderIndex];
            childrenWithDropPlaceholders.push(buildItemDropPlaceholderNode(dropPlaceholderPath, node, itemsSchema));
          }
        }

        treeNode.children = childrenWithDropPlaceholders;
      }
    }

    if (canBuildAddOrDropNodes) {
      treeNode.children.push(buildAddArrayItemNode(nodeData.path, node, itemsSchema));
    }
  }

  return treeNode;
};

const isSingleSchemaDefinition = (fieldSchema: SchemaDefinition): boolean => {
  return (fieldSchema as SchemaDefinition).oneOf === undefined || fieldSchema.discriminator !== undefined;
};

export const determineFieldSchema = (
  fieldSchema: SchemaDefinition,
): { isNullable: boolean; fieldSchema: SchemaDefinition } => {
  if (isSingleSchemaDefinition(fieldSchema)) {
    return {
      isNullable: false,
      fieldSchema,
    };
  } else {
    const [schema1, schema2] = fieldSchema.oneOf ?? [];

    const { oneOf, ...rest } = fieldSchema;
    if (schema1.type === 'null') {
      return { isNullable: true, fieldSchema: { ...schema2, ...rest } };
    } else {
      return { isNullable: true, fieldSchema: { ...schema1, ...rest } };
    }
  }
};

export const determineSelectableFieldSchema = (
  fieldSchema: SchemaDefinition,
  value: JSONValue,
): SchemaDefinition | null => {
  if (!isObject(value) || fieldSchema.oneOf === undefined) {
    return null;
  }

  const valueAsObject = value as JSONObject;
  for (const oneOfSchema of fieldSchema.oneOf) {
    const discriminatorValue = (oneOfSchema?.properties?.[discriminatorFieldName].const as string) ?? '';

    if (valueAsObject[discriminatorFieldName] === discriminatorValue) {
      return oneOfSchema;
    }
  }

  return null;
};

export const getOneOfSchemaDefaults = (
  fieldSchema: SchemaDefinition,
  engine: JsonSchemaEngineId = DEFAULT_JSON_SCHEMA_ENGINE,
): Record<string, JSONValue> => {
  if (fieldSchema.oneOf === undefined) {
    return {};
  }

  const { oneOf, discriminator, default: _default, ...rest } = fieldSchema;

  const result: Record<string, JSONValue> = {};

  for (const oneOfSchema of oneOf) {
    const discriminatorValue = (oneOfSchema?.properties?.[discriminatorFieldName].const as string) ?? '';
    const option = jsonSchemaValidationService.generateDefaults<object>(engine, { ...rest, ...oneOfSchema }) ?? {};
    result[discriminatorValue] = {
      ...option,
      [discriminatorFieldName]: discriminatorValue,
    };
  }

  return result;
};

interface FailedNodeInfo {
  lastFailedNodeIndex: number;
  failedIndices: number[];
  beforeFailedIndices: number[];
}

export const findNodeByKey = (root: ConfigurationNodeView, targetKey: string): ConfigurationNodeView | undefined => {
  if (root.key === targetKey) return root;
  for (const child of root.children ?? []) {
    const foundChild = findNodeByKey(child, targetKey);
    if (foundChild) return foundChild;
  }
  return undefined;
};

export const getDirectErrorKeys = (failedMap: ConfigurationErrors, parentKey: string): Set<string> => {
  const directErrorKeys = new Set<string>();
  const prefix = parentKey === '/' ? '/' : `${parentKey}/`;
  for (const key of Object.keys(failedMap)) {
    if (key === parentKey) continue;
    if (!key.startsWith(prefix)) continue;
    const rest = key.slice(prefix.length);
    const [firstTreeLevel] = rest.split('/');
    if (firstTreeLevel) {
      directErrorKeys.add(parentKey === '/' ? `/${firstTreeLevel}` : `${parentKey}/${firstTreeLevel}`);
    }
  }
  return directErrorKeys;
};

export const getFailedNodeInfo = (
  nodesDictionary: NodesDictionary,
  failedMap: ConfigurationErrors,
  parentKey: string,
): FailedNodeInfo | null => {
  const parent = nodesDictionary[parentKey];
  if (!parent || !parent.children?.length) return null;

  const directErrorKeys = getDirectErrorKeys(failedMap, parentKey);
  const failedIndices: number[] = [];

  // find child nodes with errors
  for (const child of parent.children) {
    if (directErrorKeys.has(child.key)) {
      failedIndices.push(child.index);
    }
  }

  if (failedIndices.length === 0) {
    return null;
  }

  const lastFailedNodeIndex = failedIndices[failedIndices.length - 1];
  const beforeFailedIndices = Array.from({ length: lastFailedNodeIndex }, (_, index) => index).filter(
    (index) => !failedIndices.includes(index),
  );

  return { failedIndices, lastFailedNodeIndex, beforeFailedIndices };
};

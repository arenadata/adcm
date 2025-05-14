import type {
  ConfigurationData,
  ConfigurationSchema,
  SchemaDefinition,
  ConfigurationErrors,
  SingleSchemaDefinition,
  MultipleSchemaDefinitions,
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
} from '../ConfigurationEditor.types';
import { validate as validateJsonSchema } from '@utils/jsonSchema/jsonSchemaUtils';
import {
  primitiveFieldTypes,
  rootNodeKey,
  rootNodeTitle,
  secretFieldValuePrefixToIgnore,
} from './ConfigurationTree.constants';

export const validate = (schema: SchemaDefinition, configuration: JSONObject, attributes: ConfigurationAttributes) => {
  const errors = validateJsonSchema(schema, configuration);

  const configurationErrors = getConfigurationErrors(errors);
  filterConfigurationErrors(configurationErrors, attributes);
  fillParentPathParts(configurationErrors);

  const isValid = Object.keys(configurationErrors).length === 0;

  return { isValid, configurationErrors };
};

export const getConfigurationErrors = (errors: ReturnType<typeof validateJsonSchema>) => {
  const result: ConfigurationErrors = {};

  const addError = (path: string, schema: SchemaDefinition, value: unknown, keyword: string, message: string) => {
    if (!result[path]) {
      result[path] = { schema, value, messages: {} };
    }

    const fieldErrors = result[path] as FieldErrors;
    fieldErrors.messages[keyword] = message;
  };

  if (!errors || errors.length === 0) {
    return result;
  }

  // group error by fieldPath
  for (const error of errors) {
    addError(
      error.instancePath,
      error.parentSchema as SchemaDefinition,
      error.data,
      error.keyword,
      error.message || '',
    );

    // config tree generates from schema. And we must show missing property error on property node
    // extend error from structure to field,
    if (error.keyword === 'required') {
      const fieldPath = `${error.instancePath}/${error.params.missingProperty}`;
      addError(fieldPath, error.parentSchema as SchemaDefinition, error.data, error.keyword, 'required');
    }
  }

  return result;
};

export const filterConfigurationErrors = (errors: ConfigurationErrors, attributes: ConfigurationAttributes) => {
  // ignore errors for not active groups
  for (const [path, value] of Object.entries(attributes)) {
    if (value.isActive === false) {
      for (const [errorPath] of Object.entries(errors)) {
        if (errorPath === path || errorPath.startsWith(`${path}/`)) {
          delete errors[errorPath];
        }
      }
    }
  }

  for (const [errorPath, error] of Object.entries(errors)) {
    const fieldErrors = error as FieldErrors;
    const { fieldSchema } = determineFieldSchema(fieldErrors.schema);

    if (fieldSchema.type === 'string' && fieldSchema.adcmMeta.isSecret) {
      const fieldValue = fieldErrors.value as string;
      const isIgnoredKeyword =
        fieldErrors.messages.pattern || fieldErrors.messages.minLength || fieldErrors.messages.maxLength;

      // ignore hashed secrets from backend
      if (isIgnoredKeyword && fieldValue.startsWith(secretFieldValuePrefixToIgnore)) {
        delete errors[errorPath];
      }
    }
  }
};

export const fillParentPathParts = (errors: ConfigurationErrors) => {
  // root always has children with errors
  if (Object.keys(errors).length > 0) {
    errors['/'] = true;
  }

  // errorPath - is full path to field
  // like /configuration/cluster/clusterName
  for (const errorPath of Object.keys(errors)) {
    const parts = errorPath.split('/');
    let path = '';

    // skip first part and last:
    // - first part is empty string
    // - last part represents full path and it already exists in errors
    for (let i = 1; i < parts.length - 1; i++) {
      const part = parts[i];
      path = `${path}/${part}`;

      if (!errors[path]) {
        errors[path] = true;
      }
    }
  }
};

export const getTitle = (keyName: string, fieldSchema: SingleSchemaDefinition) =>
  fieldSchema.title?.length ? fieldSchema.title : keyName;

export const getDefaultValue = (keyName: string, node: SingleSchemaDefinition, parentNode: SingleSchemaDefinition) =>
  node.default !== undefined ? node.default : parentNode.default?.[keyName as keyof typeof parentNode.default];

const getDefaultFieldSchema = (parentFieldSchema: SingleSchemaDefinition | null): SingleSchemaDefinition => {
  const fieldSchema: SingleSchemaDefinition = {
    type: 'string',
    readOnly: false,
    adcmMeta: {
      activation: null,
      isSecret: false,
      synchronization: null,
    },
  };

  if (parentFieldSchema?.adcmMeta.isSecret) {
    fieldSchema.adcmMeta.isSecret = true;
  }

  if (parentFieldSchema?.readOnly) {
    fieldSchema.readOnly = true;
  }

  return fieldSchema;
};

const getIsReadonly = (
  fieldSchema: SingleSchemaDefinition,
  fieldAttributes: FieldAttributes,
  parentNode: ConfigurationNode,
) => {
  const parentNodeData = parentNode.data as ConfigurationObject | ConfigurationArray;

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

  return fieldSchema.readOnly || parentNodeData.isReadonly;
};

const getNodeProps = (
  fieldName: string,
  fieldSchema: SingleSchemaDefinition,
  isNullable: boolean,
  fieldAttributes: FieldAttributes,
  parentNode: ConfigurationNode,
) => {
  const parentNodeData = parentNode.data;

  const isArrayItem = parentNodeData.fieldSchema.type === 'array';
  const title = isArrayItem ? `${parentNodeData.title} [${fieldName}]` : getTitle(fieldName, fieldSchema);

  let isRequiredField = false;
  if (parentNodeData.fieldSchema.type === 'object') {
    const requiredFields = parentNodeData.fieldSchema.required ?? [];
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
): ConfigurationNode => {
  const rootNode = buildRootNode(schema, configuration, attributes);
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

const buildRootNode = (
  schema: ConfigurationSchema,
  configuration: ConfigurationData,
  attributes: ConfigurationAttributes,
): ConfigurationNode => {
  const { fieldSchema } = determineFieldSchema(schema);
  const rootNode: ConfigurationNode = {
    key: rootNodeKey,
    data: {
      title: getTitle(rootNodeTitle, fieldSchema),
      type: 'object',
      path: [],
      parentNode: {} as ConfigurationNode,
      fieldSchema,
      isNullable: false,
      isDeletable: false,
      isReadonly: false,
      isCleanable: false,
      isDraggable: false,
      objectType: 'structure',
      value: configuration,
    },
  };

  const children: ConfigurationNode[] = [];
  if (fieldSchema.properties) {
    for (const key of Object.keys(fieldSchema.properties)) {
      children.push(buildNode(key, [key], rootNode, fieldSchema.properties[key], configuration[key], attributes));
    }
  }

  rootNode.children = children;

  return rootNode;
};

const buildNode = (
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SchemaDefinition,
  fieldValue: JSONValue,
  attributes: ConfigurationAttributes,
): ConfigurationNode => {
  const { fieldSchema: singleFieldSchema, isNullable } = determineFieldSchema(fieldSchema);
  if (singleFieldSchema.type === 'object') {
    return buildObjectNode(fieldName, path, parentNode, singleFieldSchema, isNullable, fieldValue, attributes);
  } else if (singleFieldSchema.type === 'array') {
    return buildArrayNode(fieldName, path, parentNode, singleFieldSchema, isNullable, fieldValue, attributes);
  } else if (primitiveFieldTypes.has(singleFieldSchema.type as string)) {
    return buildFieldNode(fieldName, path, parentNode, singleFieldSchema, isNullable, fieldValue, attributes);
  } else if (singleFieldSchema.type === undefined && singleFieldSchema.enum) {
    return buildFieldNode(fieldName, path, parentNode, singleFieldSchema, isNullable, fieldValue, attributes);
  } else {
    return buildUnknownNode(fieldName, path, parentNode, singleFieldSchema);
  }
};

const buildObjectNode = (
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SingleSchemaDefinition,
  isNullable: boolean,
  fieldValue: JSONValue,
  attributes: ConfigurationAttributes,
) => {
  const objectValue = fieldValue as JSONObject | null;

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
      defaultValue: getDefaultValue(title, fieldSchema, parentNode.data.fieldSchema) as JSONPrimitive,
      value: fieldValue,
      fieldAttributes,
    },
  };

  const nodeData = node.data as ConfigurationObject;
  const children = [];

  if (fieldSchema === undefined || fieldSchema.properties === undefined) {
    const fullPath = [...path, fieldName];
    console.error(`schema for /${fullPath.join('/')} not found`);
  } else {
    const addedFields = new Set();

    if (!fieldSchema.additionalProperties) {
      nodeData.objectType = 'structure';
    }

    if (objectValue) {
      // add children from schema
      for (const key of Object.keys(fieldSchema.properties)) {
        const fieldPath = [...path, key];
        const propertyValue = objectValue?.[key] ?? null;
        const childrenFieldSchema = fieldSchema.properties[key];

        children.push(buildNode(key, fieldPath, node, childrenFieldSchema, propertyValue, attributes));
        addedFields.add(key);
      }

      // add children from data (map case)
      for (const [key, propertyValue] of Object.entries(objectValue)) {
        if (!addedFields.has(key)) {
          const fieldPath = [...path, key];
          const childrenFieldSchema = fieldSchema.properties[key] ?? getDefaultFieldSchema(node.data.fieldSchema);

          children.push(buildNode(key, fieldPath, node, childrenFieldSchema, propertyValue, attributes));
          addedFields.add(key);
        }
      }
    }
  }

  if (children.length) {
    node.children = children;
  }

  return node;
};

const buildFieldNode = (
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SingleSchemaDefinition,
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
    data: {
      title,
      type: 'field',
      path,
      parentNode,
      fieldSchema,
      isNullable,
      defaultValue: getDefaultValue(title, fieldSchema, parentNode.data.fieldSchema) as JSONPrimitive,
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
  fieldSchema: SingleSchemaDefinition,
  parentNode: ConfigurationNode,
) => {
  const node: ConfigurationNodeView = {
    key: buildKey([...path, 'addEmptyObjectButton']),
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
  const fieldSchema: SingleSchemaDefinition = getDefaultFieldSchema(parentNode.data.fieldSchema);

  const node: ConfigurationNodeView = {
    key: buildKey([...path, 'addFieldButton']),
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
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SingleSchemaDefinition,
  isNullable: boolean,
  fieldValue: JSONValue,
  attributes: ConfigurationAttributes,
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
      defaultValue: getDefaultValue(title, fieldSchema, parentNode.data.fieldSchema) as JSONPrimitive,
      value: array,
      fieldAttributes,
    },
  };

  const itemsSchema = fieldSchema.items as SingleSchemaDefinition;
  node.children = [];

  if (array) {
    for (let i = 0; i < array.length; i++) {
      const elementPath = [...path, i];
      node.children.push(buildNode(i.toString(), elementPath, node, itemsSchema, array[i], attributes));
    }
  }

  return node;
};

const buildAddArrayItemNode = (
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SingleSchemaDefinition,
) => {
  const node: ConfigurationNodeView = {
    key: buildKey([...path, 'addArrayItemButton']),
    data: {
      type: 'addArrayItem',
      title: '1',
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
  fieldSchema: SingleSchemaDefinition,
) => {
  const node: ConfigurationNodeView = {
    key: buildKey([...path, 'itemDropPlaceholder']),
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
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SingleSchemaDefinition,
) => {
  const node: ConfigurationNode = {
    key: buildKey(path),
    data: {
      title: `UNKNOWN FIELD: ${fieldName}, TYPE: ${fieldSchema.type}`,
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
    (filter.showInvisible ? true : !treeNode.data.fieldSchema.adcmMeta.isInvisible) &&
    (filter.showAdvanced ? true : !treeNode.data.fieldSchema.adcmMeta.isAdvanced);

  if (!isVisible) {
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
    const itemsSchema = nodeData.fieldSchema.items as SingleSchemaDefinition;
    if (treeNode.children === undefined) {
      treeNode.children = [];
    }

    // add drop placeholders on drag
    if (treeState?.dragNode?.data && treeNode.children.length) {
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

    treeNode.children.push(buildAddArrayItemNode(nodeData.path, node, itemsSchema));
  }

  return treeNode;
};

const isSingleSchemaDefinition = (fieldSchema: SchemaDefinition): fieldSchema is SingleSchemaDefinition => {
  return (fieldSchema as MultipleSchemaDefinitions).oneOf === undefined;
};

export const determineFieldSchema = (
  fieldSchema: SchemaDefinition,
): { isNullable: boolean; fieldSchema: SingleSchemaDefinition } => {
  if (isSingleSchemaDefinition(fieldSchema)) {
    return {
      isNullable: false,
      fieldSchema,
    };
  } else {
    const [schema1, schema2] = fieldSchema.oneOf ?? [];

    if (schema1.type === 'null') {
      return { isNullable: true, fieldSchema: schema2 as SingleSchemaDefinition };
    } else {
      return { isNullable: true, fieldSchema: schema1 as SingleSchemaDefinition };
    }
  }
};

import {
  Configuration,
  ConfigurationSchema,
  SchemaDefinition,
  SingleSchemaDefinition,
  MultipleSchemaDefinitions,
  ConfigurationAttributes,
} from '@models/adcm';
import { JSONValue, JSONObject, JSONPrimitive } from '@models/json';
import { ConfigurationNode, ConfigurationNodeFilter, ConfigurationNodePath } from '../ConfigurationEditor.types';
import { isObject } from '@utils/objectUtils';

const getTitle = (keyName: string, fieldSchema: SingleSchemaDefinition) => fieldSchema.title ?? keyName;

const getDefaultFieldSchema = (): SingleSchemaDefinition => ({
  type: 'string',
  readOnly: false,
  adcmMeta: {
    activation: null,
    nullValue: null,
    synchronization: null,
  },
});

export const buildTreeNodes = (
  schema: ConfigurationSchema,
  configuration: Configuration,
  attributes: ConfigurationAttributes,
): ConfigurationNode => {
  const rootNode = buildRootNode(schema, configuration);
  fillFieldAttributes(rootNode, attributes);
  return rootNode;
};

const buildRootNode = (schema: ConfigurationSchema, configuration: Configuration): ConfigurationNode => {
  const fieldSchema = determineFieldSchema(schema);
  const rootNode: ConfigurationNode = {
    key: 'root-node',
    data: {
      title: getTitle('Configuration', fieldSchema),
      type: 'object',
      fieldSchema,
      path: [],
      isDeletable: false,
      isReadonly: true,
    },
  };

  const children: ConfigurationNode[] = [];
  if (fieldSchema.properties) {
    for (const key of Object.keys(configuration)) {
      children.push(buildNode(key, [key], rootNode, fieldSchema.properties[key], configuration[key]));
    }
  }

  rootNode.children = children;

  return rootNode;
};

const fieldTypes = new Set(['string', 'number', 'boolean']);

const buildNode = (
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SchemaDefinition,
  fieldValue: JSONValue,
): ConfigurationNode => {
  const singleFieldSchema = determineFieldSchema(fieldSchema);
  if (isObject(fieldValue)) {
    return buildObjectNode(fieldName, path, parentNode, singleFieldSchema, fieldValue);
  } else if (Array.isArray(fieldValue)) {
    return buildArrayNode(fieldName, path, parentNode, singleFieldSchema, fieldValue);
  } else if (fieldTypes.has(typeof fieldValue) || fieldValue === null) {
    return buildFieldNode(fieldName, path, parentNode, singleFieldSchema, fieldValue);
  } else {
    return buildUnknownNode(fieldName, path, singleFieldSchema);
  }
};

const buildObjectNode = (
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SingleSchemaDefinition,
  fieldValue: JSONValue,
) => {
  const objectValue = fieldValue as JSONObject;
  const isArrayItem = parentNode.data.fieldSchema.type === 'array';

  const node: ConfigurationNode = {
    key: buildKey(path),
    data: {
      title: (isArrayItem ? `[${fieldName}] ` : '') + getTitle(fieldName, fieldSchema),
      type: 'object',
      fieldSchema,
      path,
      isDeletable: isArrayItem,
      isReadonly: Boolean(fieldSchema.readOnly),
    },
  };

  const children = [];
  if (fieldSchema === undefined || fieldSchema.properties === undefined) {
    console.error(`schema for ${path}/${fieldName} not found`);
  } else {
    for (const [key, value] of Object.entries(objectValue)) {
      const fieldPath = [...path, key];
      children.push(buildNode(key, fieldPath, node, fieldSchema.properties[key] ?? getDefaultFieldSchema(), value));
    }
    if (fieldSchema.additionalProperties && !fieldSchema.readOnly) {
      children.push(buildAddFieldNode(path, node));
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
  fieldValue: JSONValue,
) => {
  let isRequiredField = false;
  if (parentNode.data.fieldSchema.type === 'object') {
    const requiredFields = parentNode.data.fieldSchema.required ?? [];
    isRequiredField = requiredFields.includes(fieldName);
  }

  const node: ConfigurationNode = {
    key: buildKey(path),
    data: {
      title: getTitle(fieldName, fieldSchema),
      type: 'field',
      fieldSchema,
      value: fieldValue as JSONPrimitive,
      path,
      isDeletable: !isRequiredField,
      isReadonly: Boolean(fieldSchema.readOnly),
    },
  };

  return node;
};

const buildAddFieldNode = (path: ConfigurationNodePath, parentNode: ConfigurationNode) => {
  const fieldSchema: SingleSchemaDefinition = getDefaultFieldSchema();

  if (parentNode.data.fieldSchema.adcmMeta.isSecret) {
    fieldSchema.adcmMeta.isSecret = true;
  }

  const node: ConfigurationNode = {
    key: buildKey(path),
    data: {
      type: 'addField',
      title: '+',
      fieldSchema,
      path,
    },
  };

  return node;
};

const buildArrayNode = (
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SingleSchemaDefinition,
  fieldValue: JSONValue,
) => {
  const array = fieldValue as Array<JSONValue>;
  const itemsSchema = fieldSchema.items as SingleSchemaDefinition;

  const node: ConfigurationNode = {
    key: buildKey(path),
    data: {
      title: getTitle(fieldName, fieldSchema),
      type: 'array',
      fieldSchema,
      path,
      isReadonly: Boolean(fieldSchema.readOnly),
    },
  };

  node.children = [];

  for (let i = 0; i < array.length; i++) {
    const elementPath = [...path, i];
    node.children.push(buildArrayItemNode(i.toString(), elementPath, node, itemsSchema, array[i]));
  }

  if (!node.data.fieldSchema.readOnly) {
    node.children.push(buildAddArrayItemNode(path, itemsSchema));
  }

  return node;
};

const buildArrayItemNode = (
  fieldName: string,
  path: ConfigurationNodePath,
  parentNode: ConfigurationNode,
  fieldSchema: SingleSchemaDefinition,
  fieldValue: JSONValue,
) => {
  return buildNode(fieldName, path, parentNode, fieldSchema, fieldValue);
};

const buildAddArrayItemNode = (path: ConfigurationNodePath, fieldSchema: SingleSchemaDefinition) => {
  const node: ConfigurationNode = {
    key: buildKey(path),
    data: {
      type: 'addArrayItem',
      title: '+',
      fieldSchema,
      path,
    },
  };

  return node;
};

const buildUnknownNode = (fieldName: string, path: ConfigurationNodePath, fieldSchema: SingleSchemaDefinition) => {
  const node: ConfigurationNode = {
    key: buildKey(path),
    data: {
      title: `UNKNOWN FIELD: ${fieldName}, TYPE: ${fieldSchema.type}`,
      type: 'field',
      fieldSchema,
      value: 'some value',
      path,
      isDeletable: false,
      isReadonly: true,
    },
  };

  return node;
};

const buildKey = (path: ConfigurationNodePath) => `/${path.join('/')}`;

export const filterTreeNodes = (tree: ConfigurationNode, filter: ConfigurationNodeFilter) => {
  tree.children = tree.children?.filter((node) => filterRecursively(node, filter));
  return tree;
};

const filterRecursively = (tree: ConfigurationNode, filter: ConfigurationNodeFilter) => {
  const foundInTitle = tree.data.title.includes(filter.title);
  const isVisible =
    (filter.showInvisible ? true : !tree.data.fieldSchema.adcmMeta.isInvisible) &&
    (filter.showAdvanced ? true : !tree.data.fieldSchema.adcmMeta.isAdvanced);

  tree.children = tree.children?.filter((node) => filterRecursively(node, filter));

  const foundInChildren = Boolean(tree.children?.length);
  if ((foundInTitle || foundInChildren) && isVisible) {
    return true;
  }

  return false;
};

const fillFieldAttributes = (tree: ConfigurationNode, attributes: ConfigurationAttributes) => {
  tree.data.fieldAttributes = attributes[tree.key];
  if (tree.children) {
    for (const child of tree.children) {
      fillFieldAttributes(child, attributes);
    }
  }
};

const isSingleSchemaDefinition = (fieldSchema: SchemaDefinition): fieldSchema is SingleSchemaDefinition => {
  return (fieldSchema as MultipleSchemaDefinitions).oneOf === undefined;
};

const determineFieldSchema = (fieldSchema: SchemaDefinition): SingleSchemaDefinition => {
  if (isSingleSchemaDefinition(fieldSchema)) {
    return fieldSchema as SingleSchemaDefinition;
  } else {
    for (const someSchema of fieldSchema.oneOf ?? []) {
      if (someSchema.type !== 'null') {
        return someSchema;
      }
    }
  }

  return getDefaultFieldSchema();
};

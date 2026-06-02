import type { ConfigurationData, SchemaDefinition } from '@models/adcm';
import type { JSONObject, JSONPrimitive, JSONValue } from '@models/json';
import type { ConfigurationNodePath } from './ConfigurationEditor.types';
import { generateJsonSchemaDefaults } from '@utils/jsonSchema/JsonSchemaValidationService';
import { deepClone, isObject } from '@utils/objectUtils';
import { isValueUnset } from '@utils/checkUtils';

export const editField = (configuration: ConfigurationData, path: ConfigurationNodePath, value: JSONValue) => {
  if (path.length) {
    const newConfiguration = deepClone<ConfigurationData>(configuration);

    const fieldName = path.pop()!;

    let node = newConfiguration;
    for (const part of path) {
      node = node[part] as JSONObject;
    }

    node[fieldName] = value;

    return newConfiguration;
  }
};

export const addField = (configuration: ConfigurationData, path: ConfigurationNodePath, value: JSONPrimitive) => {
  const newConfiguration = deepClone<ConfigurationData>(configuration);

  const fieldName = path.pop()!;

  let node = newConfiguration;
  for (const part of path) {
    // handle case when map / secretMap is required, but not set or must be defined by user
    if (path.at(-1) === part && isValueUnset(node[part])) {
      node[part] = {};
    }
    node = node[part] as JSONObject;
  }

  node[fieldName] = value;

  return newConfiguration;
};

export const deleteField = (configuration: ConfigurationData, path: ConfigurationNodePath) => {
  const newConfiguration = deepClone<ConfigurationData>(configuration);

  const fieldName = path.pop()!;

  let node = newConfiguration;
  for (const part of path) {
    node = node[part] as JSONObject;
  }

  delete node[fieldName];

  return newConfiguration;
};

export const addArrayItem = (
  configuration: ConfigurationData,
  path: ConfigurationNodePath,
  schema: SchemaDefinition,
) => {
  const newConfiguration = deepClone<ConfigurationData>(configuration);

  let node = newConfiguration;
  for (const part of path) {
    // handle case when array is required, but not set or must be defined by user
    if (path.at(-1) === part && isValueUnset(node[part])) {
      node[part] = [];
    }

    node = node[part] as JSONObject;
  }

  const newItem = generateJsonSchemaDefaults(schema);
  // we need this check because initially node is an object
  if (Array.isArray(node)) {
    node.push(newItem);
  }

  return newConfiguration;
};

export const deleteArrayItem = (configuration: ConfigurationData, path: ConfigurationNodePath) => {
  const newConfiguration = deepClone<ConfigurationData>(configuration);

  const fieldName = path.pop()!;

  let node = newConfiguration;
  for (const part of path) {
    node = node[part] as JSONObject;
  }

  // we need this check because initially node is an object
  if (Array.isArray(node)) {
    node.splice(fieldName as number, 1);
  }

  return newConfiguration;
};

export const moveArrayItem = (
  configuration: ConfigurationData,
  currentPath: ConfigurationNodePath,
  newPath: ConfigurationNodePath,
) => {
  const newConfiguration = deepClone<ConfigurationData>(configuration);

  const currentIndex = Number(currentPath.pop()!);
  const newIndex = Number(newPath.pop()!);

  let node = newConfiguration;
  for (const part of currentPath) {
    node = node[part] as JSONObject;
  }

  const arrayNode = node as unknown as [];
  const tmp = arrayNode[currentIndex];

  // moving forward item
  if (currentIndex < newIndex) {
    // moving all elements one position backwards
    for (let i = currentIndex; i < newIndex; i++) {
      arrayNode[i] = arrayNode[i + 1];
    }

    arrayNode[newIndex] = tmp;
  } else if (newIndex < currentIndex) {
    // moving all elements one position forward
    for (let i = currentIndex; i > newIndex; i--) {
      arrayNode[i] = arrayNode[i - 1];
    }

    arrayNode[newIndex] = tmp;
  }

  return newConfiguration;
};

export const removeEmpty = (value: unknown): unknown => {
  if (isObject(value)) {
    const newObject: JSONObject = {};
    const obj = value as JSONObject;
    Object.keys(obj).forEach((key) => {
      if (isObject(obj[key])) {
        newObject[key] = removeEmpty(obj[key]) as JSONValue;
      } else if (Array.isArray(obj[key])) {
        newObject[key] = (obj[key] as unknown[]).map((v) => removeEmpty(v)) as JSONValue;
      } else if (obj[key] !== undefined) {
        newObject[key] = obj[key];
      }
    });
    return newObject;
  }

  return value;
};

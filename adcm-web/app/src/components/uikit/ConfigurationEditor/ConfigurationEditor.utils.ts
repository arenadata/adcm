import type { ConfigurationData, SchemaDefinition } from '@models/adcm';
import type { JSONObject, JSONPrimitive, JSONValue } from '@models/json';
import type { ConfigurationNodePath } from './ConfigurationEditor.types';
import { generateFromSchema } from '@utils/jsonSchema/jsonSchemaUtils';
import { isObject } from '@utils/objectUtils';

export const editField = (configuration: ConfigurationData, path: ConfigurationNodePath, value: JSONValue) => {
  if (path.length) {
    const newConfiguration = cloneConfiguration(configuration);

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
  const newConfiguration = cloneConfiguration(configuration);

  const fieldName = path.pop()!;

  let node = newConfiguration;
  for (const part of path) {
    // handle case when map / secretMap is required, but not set or must be defined by user
    if (path.at(-1) === part && node[part] === undefined) {
      node[part] = {};
    }
    node = node[part] as JSONObject;
  }

  node[fieldName] = value;

  return newConfiguration;
};

export const deleteField = (configuration: ConfigurationData, path: ConfigurationNodePath) => {
  const newConfiguration = cloneConfiguration(configuration);

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
  const newConfiguration = cloneConfiguration(configuration);

  let node = newConfiguration;
  for (const part of path) {
    // handle case when array is required, but not set or must be defined by user
    if (path.at(-1) === part && node[part] === undefined) {
      node[part] = [];
    }

    node = node[part] as JSONObject;
  }

  const newItem = generateFromSchema(schema);
  // we need this check because initially node is an object
  if (Array.isArray(node)) {
    node.push(newItem);
  }

  return newConfiguration;
};

export const deleteArrayItem = (configuration: ConfigurationData, path: ConfigurationNodePath) => {
  const newConfiguration = cloneConfiguration(configuration);

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

const cloneConfiguration = (configuration: ConfigurationData) => {
  return structuredClone(configuration);
};

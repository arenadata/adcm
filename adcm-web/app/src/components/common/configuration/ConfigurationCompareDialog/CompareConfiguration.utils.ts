import {
  ConfigurationAttributes,
  ConfigurationData,
  ConfigurationSchema,
  SchemaDefinition,
  SingleSchemaDefinition,
} from '@models/adcm';
import { determineFieldSchema, getTitle } from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree.utils';
import { JSONObject, JSONValue } from '@models/json';

export const getCompareView = (
  schema: ConfigurationSchema,
  configuration: ConfigurationData,
  attributes: ConfigurationAttributes,
) => {
  const { fieldSchema } = determineFieldSchema(schema);

  return getCompareViewObject(fieldSchema, configuration, attributes, '');
};

type GetCompareViewItemRes = {
  title: string;
  value: JSONValue;
};

const getCompareViewItem = (
  key: string,
  schema: SchemaDefinition,
  fieldValue: JSONValue,
  attributes: ConfigurationAttributes,
  parentPath: string,
  isParentDeactivated = false,
): GetCompareViewItemRes | null => {
  const { fieldSchema } = determineFieldSchema(schema);

  if (fieldSchema.adcmMeta.isInvisible) {
    return null;
  }

  let title = getTitle(key, fieldSchema);

  const itemPath = `${parentPath}/${key}`;
  const itemAttributes = attributes[itemPath];
  const isDeactivated = isParentDeactivated || itemAttributes?.isActive === false;
  if (isDeactivated) {
    title = `// ${title}`;
  }

  let value: JSONValue;

  if (Array.isArray(fieldValue)) {
    value = getCompareViewArray(fieldSchema, fieldValue, attributes, itemPath);
  } else if (typeof fieldValue === 'object' && fieldValue !== null) {
    value = getCompareViewObject(fieldSchema, fieldValue, attributes, itemPath, isDeactivated);
  } else {
    value = fieldValue;
  }

  return {
    title,
    value,
  };
};

const getCompareViewArray = (
  fieldSchema: SingleSchemaDefinition,
  fieldValue: JSONValue,
  attributes: ConfigurationAttributes,
  parentPath: string,
) => {
  const res = [];
  const array = fieldValue as Array<JSONValue>;
  const itemsSchema = fieldSchema.items as SingleSchemaDefinition;
  for (let i = 0; i < array.length; i++) {
    const tmp = getCompareViewItem(i.toString(), itemsSchema, array[i], attributes, parentPath + '/' + i);
    if (tmp === null) continue;

    res.push(tmp.value);
  }

  return res;
};

const getCompareViewObject = (
  fieldSchema: SingleSchemaDefinition,
  fieldValue: JSONObject,
  attributes: ConfigurationAttributes,
  parentPath: string,
  isParentDeactivated = false,
) => {
  if (!fieldSchema.properties) return fieldValue;

  const result: JSONObject = {};

  for (const key of Object.keys(fieldValue)) {
    if (!fieldSchema.properties[key]) {
      result[key] = fieldValue[key];
      continue;
    }

    const tmp = getCompareViewItem(
      key,
      fieldSchema.properties[key],
      fieldValue[key],
      attributes,
      parentPath,
      isParentDeactivated,
    );
    if (tmp === null) continue;

    const { title, value } = tmp;

    result[title] = value;
  }

  return result;
};

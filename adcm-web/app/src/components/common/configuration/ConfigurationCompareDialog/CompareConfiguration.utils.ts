import { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { JSONObject, JSONValue } from '@models/json';
// eslint-disable-next-line spellcheck/spell-checker
// TODO: import from @uikit, after fix jest paths
import { ConfigurationNode } from '../../../uikit/ConfigurationEditor/ConfigurationEditor.types';
import { buildConfigurationNodes } from '../../../uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree.utils';

type NameValueTuple = { name: string; value: JSONValue };

export const getCompareView = (
  schema: ConfigurationSchema,
  configuration: ConfigurationData,
  attributes: ConfigurationAttributes,
): JSONObject => {
  const result: JSONObject = {};
  const configNode = buildConfigurationNodes(schema, configuration, attributes);

  if (configNode.children) {
    for (const child of configNode.children) {
      const tuple = configNodeToCompareView(child);
      if (tuple) {
        result[tuple.name] = tuple.value;
      }
    }
  }

  return result;
};

const configNodeToCompareView = (configNode: ConfigurationNode, isParentDeactivated = false): NameValueTuple | null => {
  if (configNode.data.fieldSchema.adcmMeta.isInvisible) {
    return null;
  }

  const isDeactivated = isParentDeactivated || configNode.data.fieldAttributes?.isActive === false;
  const title = configNode.data.title;
  const name = isDeactivated ? `// ${title}` : title;

  switch (configNode.data.type) {
    case 'field': {
      return { name, value: configNode.data.value };
    }
    case 'object': {
      const result: JSONObject = {};
      if (configNode.children) {
        for (const child of configNode.children) {
          const tuple = configNodeToCompareView(child, isDeactivated);
          if (tuple) {
            result[tuple.name] = tuple.value;
          }
        }
      }

      return { name, value: result };
    }
    case 'array': {
      const result: JSONValue[] = [];
      if (configNode.children) {
        for (const child of configNode.children) {
          const tuple = configNodeToCompareView(child);
          if (tuple) {
            result.push(tuple.value);
          }
        }
      }

      return { name, value: result };
    }
  }
};

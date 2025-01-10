import type {
  ConfigurationAttributes,
  ConfigurationData,
  ConfigurationErrors,
  ConfigurationSchema,
  SchemaDefinition,
} from '@models/adcm';
import type { JSONObject, JSONValue } from '@models/json';
import {
  buildConfigurationNodes,
  iterateConfigurationNodes,
} from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree.utils';
import type { NodesDictionary } from './AdcmConfigEditor.types';
import { swapTitleAsPropertyName as swapSchema } from '@utils/jsonSchema/jsonSchemaUtils';
import type { ConfigurationNode } from '@uikit/ConfigurationEditor/ConfigurationEditor.types';
import {
  MarkerSeverity,
  type IIdentifiedSingleEditOperation,
  type IMarker,
  type ITextModel,
  type SymbolsDictionary,
} from '../MonacoCodeEditor.types';

export const getSymbolsDictionaryWithSchema = (
  schema: SchemaDefinition,
  config: JSONObject,
  attributes: ConfigurationAttributes,
) => {
  const tree = buildConfigurationNodes(schema, config, attributes);
  const dictionary: NodesDictionary = {};

  for (const node of iterateConfigurationNodes(tree)) {
    dictionary[node.key] = node;
  }

  return dictionary;
};

export const getAdcmErrorMarkers = (
  model: ITextModel,
  errors: ConfigurationErrors,
  symbolsDictionary: SymbolsDictionary,
): IMarker[] => {
  const markers: IMarker[] = [];

  const paths = Object.keys(errors);

  for (const path of paths) {
    const error = errors[path];
    const symbol = symbolsDictionary[path];

    if (error !== true && symbol !== undefined) {
      const message = Object.values(error.messages).join(', ');
      markers.push({
        message,
        severity: MarkerSeverity.Error,
        startLineNumber: symbol.selectionRange.startLineNumber,
        startColumn: symbol.selectionRange.startColumn,
        endLineNumber: symbol.selectionRange.endLineNumber,
        endColumn: symbol.selectionRange.endColumn,
        owner: 'adcm',
        resource: model.uri,
      });
    }
  }

  return markers;
};

/**
 * @deprecated
 */
export const swapAll = (schema: SchemaDefinition, config: JSONObject, attributes: ConfigurationAttributes) => {
  const swappedSchema = swapSchema(schema) as SchemaDefinition;
  const swappedConfig = swapModel(schema, config, attributes);

  return {
    schema: swappedSchema,
    config: swappedConfig,
    attributes: attributes,
  };
};

/**
 * @deprecated
 */
// based on compare config
const swapModel = (
  schema: ConfigurationSchema,
  configuration: ConfigurationData,
  attributes: ConfigurationAttributes,
): JSONObject => {
  const result: JSONObject = {};
  const configNode = buildConfigurationNodes(schema, configuration, attributes);

  if (configNode.children) {
    for (const child of configNode.children) {
      const tuple = swapModelNode(child);
      if (tuple) {
        result[tuple.name] = tuple.value;
      }
    }
  }

  return result;
};

/**
 * @deprecated
 */
type NameValueTuple = { name: string; value: JSONValue };

/**
 * @deprecated
 */
const swapModelNode = (configNode: ConfigurationNode): NameValueTuple | null => {
  if (configNode.data.fieldSchema.adcmMeta.isInvisible) {
    return null;
  }

  const title = configNode.data.title;

  switch (configNode.data.type) {
    case 'field': {
      return { name: title, value: configNode.data.value };
    }
    case 'object': {
      const result: JSONObject = {};
      if (configNode.children) {
        for (const child of configNode.children) {
          const tuple = swapModelNode(child);
          if (tuple) {
            result[tuple.name] = tuple.value;
          }
        }
      }

      return { name: title, value: result };
    }
    case 'array': {
      const result: JSONValue[] = [];
      if (configNode.children) {
        for (const child of configNode.children) {
          const tuple = swapModelNode(child);
          if (tuple) {
            result.push(tuple.value);
          }
        }
      }

      return { name: title, value: result };
    }
  }
};

export const getCommentsAppends = (
  symbolsDictionary: SymbolsDictionary,
  nodesDictionary: NodesDictionary,
): IIdentifiedSingleEditOperation[] => {
  const appends: IIdentifiedSingleEditOperation[] = [];

  const nodesPaths = Object.keys(nodesDictionary);

  for (const path of nodesPaths) {
    const node = nodesDictionary[path];
    const symbol = symbolsDictionary[path];

    if (symbol && node) {
      let commentText = '';
      if (node.data.fieldSchema.title) {
        commentText += node.data.fieldSchema.title;
      }

      if (node.data.fieldSchema.description) {
        commentText += ` - ${node.data.fieldSchema.description}`;
      }

      if (commentText.length) {
        const spaces = ' '.repeat(symbol.range.startColumn - 1);
        appends.push({
          text: `# ${commentText}\n${spaces}`,
          range: {
            startLineNumber: symbol.range.startLineNumber,
            startColumn: symbol.range.startColumn,
            endLineNumber: symbol.range.startLineNumber,
            endColumn: symbol.range.startColumn,
          },
          forceMoveMarkers: true,
        });
      }
    }
  }

  return appends;
};

import { FieldAttributes, SingleSchemaDefinition } from '@models/adcm';
import { JSONPrimitive, JSONValue } from '@models/json';
import { Node } from '@uikit/CollapseTree2/CollapseNode.types';

export type ConfigurationNodeType = 'object' | 'field' | 'addField' | 'array' | 'addArrayItem';
export type ConfigurationNodePath = (string | number)[];

export type ConfigurationField = {
  type: 'field';
  title: string;
  fieldSchema: SingleSchemaDefinition;
  fieldAttributes?: FieldAttributes;
  parentNode: ConfigurationNode;
  value: JSONPrimitive;
  path: ConfigurationNodePath;
  isDeletable: boolean;
  isReadonly: boolean;
};

export type ConfigurationNewField = {
  type: 'addField';
  title: string;
  fieldSchema: SingleSchemaDefinition; // parent schema
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
};

export type ConfigurationObject = {
  type: 'object';
  title: string;
  fieldSchema: SingleSchemaDefinition;
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
  isDeletable: boolean;
  isReadonly: boolean;
  objectType: 'map' | 'structure';
  value: JSONValue;
};

export type ConfigurationNewEmptyObject = {
  type: 'addEmptyObject';
  title: string;
  fieldSchema: SingleSchemaDefinition; // items schema
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
};

export type ConfigurationArray = {
  type: 'array';
  title: string;
  fieldSchema: SingleSchemaDefinition;
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
  isReadonly: boolean;
  isDeletable: boolean;
  value: JSONValue;
};

export type ConfigurationNewArrayItem = {
  type: 'addArrayItem';
  title: string;
  fieldSchema: SingleSchemaDefinition; // items schema
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
};

export type ConfigurationNode = Node<
  | ConfigurationField
  | ConfigurationNewField
  | ConfigurationNewEmptyObject
  | ConfigurationObject
  | ConfigurationArray
  | ConfigurationNewArrayItem
>;

export type ConfigurationNodeFilter = {
  title: string;
  showInvisible: boolean; // false
  showAdvanced: boolean;
};

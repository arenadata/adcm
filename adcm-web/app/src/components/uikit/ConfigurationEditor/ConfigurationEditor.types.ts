import type { FieldAttributes, SchemaDefinition } from '@models/adcm';
import type { JSONObject, JSONPrimitive, JSONValue } from '@models/json';
import type { Node } from '@uikit/CollapseTree2/CollapseNode.types';

export type ConfigurationNodeType = 'object' | 'field' | 'addField' | 'array' | 'addArrayItem';
export type ConfigurationNodePath = (string | number)[];

export type ConfigurationField = {
  type: 'field';
  title: string;
  fieldSchema: SchemaDefinition;
  isNullable: boolean;
  fieldAttributes?: FieldAttributes;
  parentNode: ConfigurationNode;
  defaultValue?: JSONPrimitive;
  value: JSONPrimitive;
  path: ConfigurationNodePath;
  isDeletable: boolean;
  isCleanable: boolean;
  isReadonly: boolean;
  isDraggable: boolean;
};

export type ConfigurationNewField = {
  type: 'addField';
  title: string;
  fieldSchema: SchemaDefinition; // parent schema
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
};

export type ConfigurationObject = {
  type: 'object';
  title: string;
  fieldSchema: SchemaDefinition;
  isNullable: boolean;
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
  isDeletable: boolean;
  isReadonly: boolean;
  isCleanable: boolean;
  objectType: 'map' | 'structure';
  defaultValue?: JSONObject;
  value: JSONValue;
  isDraggable: boolean;
};

export type ConfigurationSelectableObject = {
  type: 'selectableObject';
  title: string;
  fieldSchema: SchemaDefinition;
  selectedFieldSchema: SchemaDefinition | null;
  oneOfSchemaDefaults: Record<string, JSONValue>;
  isNullable: boolean;
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
  isDeletable: boolean;
  isReadonly: boolean;
  isCleanable: boolean;
  defaultValue?: JSONObject;
  value: JSONValue;
  isDraggable: boolean;
};

export type ConfigurationNewEmptyObject = {
  type: 'addEmptyObject';
  title: string;
  fieldSchema: SchemaDefinition; // items schema
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
};

export type ConfigurationArray = {
  type: 'array';
  title: string;
  fieldSchema: SchemaDefinition;
  isNullable: boolean;
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
  isReadonly: boolean;
  isDeletable: boolean;
  isCleanable: boolean;
  defaultValue?: JSONPrimitive;
  value: JSONValue;
  isDraggable: boolean;
};

export type ConfigurationNewArrayItem = {
  type: 'addArrayItem';
  title: string;
  fieldSchema: SchemaDefinition; // items schema
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath;
};

export type ConfigurationItemDropPlaceholder = {
  type: 'dropPlaceholder';
  title: string;
  fieldSchema: SchemaDefinition; // items schema
  parentNode: ConfigurationNode;
  fieldAttributes?: FieldAttributes;
  path: ConfigurationNodePath; // new item path after drop
};

export type ConfigurationNode = Node<
  ConfigurationField | ConfigurationObject | ConfigurationSelectableObject | ConfigurationArray
>;

export type ConfigurationNodeView = Node<
  | ConfigurationField
  | ConfigurationNewField
  | ConfigurationNewEmptyObject
  | ConfigurationObject
  | ConfigurationSelectableObject
  | ConfigurationArray
  | ConfigurationNewArrayItem
  | ConfigurationItemDropPlaceholder
>;

export type ConfigurationTreeFilter = {
  title: string;
  showInvisible: boolean;
  showAdvanced: boolean;
};

export type ConfigurationTreeState = {
  dragNode: ConfigurationNodeView | null;
};

export type NodesDictionary = { [path: string]: ConfigurationNode };

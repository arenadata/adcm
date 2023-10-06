import { JSONObject } from '../json';
import { JSONSchema7, JSONSchema7TypeName } from 'json-schema';

// eslint-disable-next-line @typescript-eslint/ban-types
type NullValue = {} | [] | null;

export interface AdcmFieldMetaData {
  isAdvanced?: boolean;
  isInvisible?: boolean;
  activation: {
    isAllowChange: boolean;
  } | null;
  synchronization: {
    isAllowChange: boolean;
  } | null;
  nullValue: NullValue;
  isSecret?: boolean;
  stringExtra?: {
    suggestions?: string[];
    isMultiline?: boolean;
  } | null;
  enumExtra?: {
    labels: string[];
  } | null;
}

type RedefinedFields = 'items' | 'properties' | 'additionalProperties' | 'oneOf';
export interface SingleSchemaDefinition extends Omit<JSONSchema7, RedefinedFields> {
  // Fields that must be redefined because they make use of this definition itself
  items?: SchemaDefinition;
  additionalItems?: SchemaDefinition;
  properties?: {
    [key: string]: SchemaDefinition;
  };
  additionalProperties?: boolean;
  adcmMeta: AdcmFieldMetaData;
}

export interface NullSchemaDefinition {
  type: 'null';
}

export type MultipleSchemaDefinitions = {
  oneOf?: (SingleSchemaDefinition | NullSchemaDefinition)[];
};

export type SchemaDefinition = SingleSchemaDefinition | MultipleSchemaDefinitions;
export type SchemaTypeName = JSONSchema7TypeName;
export type ConfigurationSchema = SchemaDefinition;
export type Configuration = JSONObject;

export type FieldAttributes = {
  isActive: boolean;
  isSynchronized: boolean;
};

export type ConfigurationAttributes = Record<string, FieldAttributes>; // key - path, value: attributes

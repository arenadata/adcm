import { JSONObject } from '../json';
import { JSONSchema7, JSONSchema7TypeName } from 'json-schema';

// eslint-disable-next-line @typescript-eslint/ban-types
type NullValue = {} | [] | null;

export interface AdcmFieldMetaData {
  isAdvanced?: boolean;
  isInvisible?: boolean;
  activation: {
    isShown: boolean;
    isAllowChange: boolean;
  } | null;
  synchronization: {
    isShown: boolean;
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
export type ConfigurationData = JSONObject;

export type FieldAttributes = {
  isActive: boolean;
  isSynchronized: boolean;
};

export type ConfigurationAttributes = Record<string, FieldAttributes>; // key - path, value: attributes

export interface AdcmConfigShortView {
  id: number;
  isCurrent: boolean;
  creationTime: string; //ISO Date
  description: string;
}

export interface AdcmConfig extends AdcmConfigShortView {
  config: ConfigurationData;
  adcmMeta: ConfigurationAttributes;
}

export interface AdcmConfiguration {
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
  schema: ConfigurationSchema;
}

export interface AdcmFullConfigurationInfo extends AdcmConfigShortView {
  configuration: AdcmConfiguration;
}

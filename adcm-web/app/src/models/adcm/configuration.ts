import type { JSONObject } from '@models/json';
import type { JSONSchema7, JSONSchema7TypeName } from 'json-schema';

export interface AdcmFieldMetaData {
  isAdvanced?: boolean;
  isInvisible?: boolean;
  activation: {
    isAllowChange: boolean;
  } | null;
  synchronization: {
    isAllowChange: boolean;
  } | null;
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
  readOnly: boolean;
}

export interface NullSchemaDefinition {
  type: 'null';
}

export type MultipleSchemaDefinitions = {
  oneOf: (SingleSchemaDefinition | NullSchemaDefinition)[];
};

export type SchemaDefinition = SingleSchemaDefinition | MultipleSchemaDefinitions;
export type SchemaTypeName = JSONSchema7TypeName;
export type ConfigurationSchema = SchemaDefinition;
export type ConfigurationData = JSONObject;

export type FieldAttributes = {
  isActive?: boolean;
  isSynchronized?: boolean;
};

export type ConfigurationAttributes = Record<FieldPath, FieldAttributes>; // key - path, value: attributes

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

export type FieldPath = string;
export type ErrorKeyword = string;
export type ErrorMessage = string;
export type FieldErrors = {
  // biome-ignore lint/suspicious/noExplicitAny:
  value: any;
  schema: SchemaDefinition;
  messages: Record<ErrorKeyword, ErrorMessage>;
};

// true as record value means that child node has error(s)
export type ConfigurationErrors = Record<FieldPath, true | FieldErrors>;

import type { JSONObject, JSONValue } from '@models/json';
import type { JSONSchema7, JSONSchema7TypeName } from 'json-schema';

export interface AdcmFieldMetaData {
  isAdvanced?: boolean;
  isInvisible?: boolean;
  activation?: {
    isAllowChange: boolean;
    default?: boolean;
  } | null;
  synchronization?: {
    isAllowChange: boolean;
    default?: boolean;
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

type RedefinedFields = 'items' | 'properties' | 'additionalProperties';

export interface SchemaDefinition extends Omit<JSONSchema7, RedefinedFields> {
  /**
   * Project uses 2020-12, while `JSONSchema7` typings cover draft-07.
   * Redefine/extend keywords we actively use in schemas so TS matches runtime behavior.
   */
  items?: SchemaDefinition | false;
  // deprecated
  additionalItems?: SchemaDefinition | false;
  // 2019-09 / 2020-12
  unevaluatedItems?: SchemaDefinition | false;
  unevaluatedProperties?: SchemaDefinition | false;
  minContains?: number;
  maxContains?: number;
  prefixItems?: SchemaDefinition[];
  properties?: {
    [key: string]: SchemaDefinition;
  };
  additionalProperties?: boolean;
  adcmMeta?: AdcmFieldMetaData;
  readOnly?: boolean;
  oneOf?: SchemaDefinition[];
  discriminator?: { propertyName: string };
  // 2019-09 / 2020-12
  dependentRequired?: Record<string, string[]>;
  dependentSchemas?: Record<string, SchemaDefinition | boolean>;
}

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
  createdBy: string;
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
  value: JSONValue;
  schema: SchemaDefinition;
  messages: Record<ErrorKeyword, ErrorMessage>;
};

// true as record value means that child node has error(s)
export type ConfigurationErrors = Record<FieldPath, true | FieldErrors>;

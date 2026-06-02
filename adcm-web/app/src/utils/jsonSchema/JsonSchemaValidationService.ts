import type { ErrorObject } from 'ajv';
import type { Schema } from 'ajv/dist/2020';
import type { ConfigurationAttributes, ConfigurationErrors, FieldErrors, SchemaDefinition } from '@models/adcm';
import type { JSONValue } from '@models/json';
import {
  nestedPropsErrorKeyword,
  nestedPropsErrorMessage,
  rootNodeKey,
  secretFieldValuePrefixToIgnore,
  DEFAULT_JSON_SCHEMA_ENGINE,
  JSON_SCHEMA_ENGINE_LOCAL_STORAGE_KEY,
} from './jsonValidationService.constants';

export { DEFAULT_JSON_SCHEMA_ENGINE, JSON_SCHEMA_ENGINE_LOCAL_STORAGE_KEY };

import { validateSchemaLikeWithAjv, generateFromSchema, type SchemaLike } from './jsonSchemaUtils';
import { generateFromSchemaWithCfWorker, validateWithCfWorker } from '@utils/jsonSchema/cfworkerSchemaUtils';

export type JsonSchemaEngineId = 'ajv' | 'cfworker';

export type AjvRawErrors = ErrorObject[] | null | undefined;

export type CfWorkerMappedErrors = ReturnType<typeof validateWithCfWorker>;

export type RawValidationErrorsByEngine = AjvRawErrors | CfWorkerMappedErrors;

export type EngineValidationError = {
  instancePath?: string;
  parentSchema?: unknown;
  data?: unknown;
  keyword: string;
  message?: string;
  params?: Record<string, unknown>;
};

class JsonSchemaValidationService {
  private getEngineOverride(): JsonSchemaEngineId | null {
    try {
      const item = window.localStorage.getItem(JSON_SCHEMA_ENGINE_LOCAL_STORAGE_KEY) as JsonSchemaEngineId | null;
      return item === 'ajv' || item === 'cfworker' ? item : null;
    } catch {
      return null;
    }
  }

  private resolveEngine(engine: JsonSchemaEngineId): JsonSchemaEngineId {
    return this.getEngineOverride() ?? engine;
  }

  validateRaw(engine: JsonSchemaEngineId, schema: SchemaLike, data: unknown): RawValidationErrorsByEngine {
    const effectiveEngine = this.resolveEngine(engine);
    if (effectiveEngine === 'cfworker') {
      return validateWithCfWorker(schema, data);
    }

    return validateSchemaLikeWithAjv(schema, data) as unknown as AjvRawErrors;
  }

  validate(
    engine: JsonSchemaEngineId,
    schema: SchemaLike,
    data: unknown,
    attributes: ConfigurationAttributes,
  ): { isValid: boolean; configurationErrors: ConfigurationErrors } {
    const effectiveEngine = this.resolveEngine(engine);
    const rawErrors = this.validateRaw(effectiveEngine, schema, data);
    return this.mapRawErrorsToConfigurationErrors(effectiveEngine, rawErrors, attributes);
  }

  mapRawErrorsToConfigurationErrors(
    engine: JsonSchemaEngineId,
    rawErrors: RawValidationErrorsByEngine | EngineValidationError[] | null | undefined,
    attributes: ConfigurationAttributes,
  ): { isValid: boolean; configurationErrors: ConfigurationErrors } {
    const effectiveEngine = this.resolveEngine(engine);
    const configurationErrors = this.mapEngineErrorsToConfigurationErrors(
      effectiveEngine,
      rawErrors as unknown as EngineValidationError[] | null | undefined,
    );

    this.filterConfigurationErrors(configurationErrors, attributes);
    this.fillParentPathParts(configurationErrors);

    const isValid = Object.keys(configurationErrors).length === 0;
    return { isValid, configurationErrors };
  }

  generateDefaults<T>(engine: JsonSchemaEngineId, schema: SchemaLike): T | null | undefined {
    const effectiveEngine = this.resolveEngine(engine);
    if (effectiveEngine === 'cfworker') {
      return generateFromSchemaWithCfWorker<T>(schema);
    }

    if (typeof schema !== 'object' || schema === null) return null;
    return generateFromSchema<T>(schema as Schema);
  }

  private normalizeConfigTreeInstancePath(instancePath: string | undefined = ''): string {
    return instancePath === '' ? rootNodeKey : instancePath;
  }

  private joinInstancePathWithSegment(instancePath: string | undefined, segment: string): string {
    const base = this.normalizeConfigTreeInstancePath(instancePath);
    return base === rootNodeKey ? `${rootNodeKey}${segment}` : `${base}/${segment}`;
  }

  private mapEngineErrorsToConfigurationErrors(
    engine: JsonSchemaEngineId,
    errors: EngineValidationError[] | null | undefined,
  ): ConfigurationErrors {
    const result: ConfigurationErrors = {};

    const addError = (path: string, schema: SchemaDefinition, value: JSONValue, keyword: string, message: string) => {
      if (!result[path]) {
        result[path] = { schema, value, messages: {} };
      }

      const fieldErrors = result[path] as FieldErrors;
      fieldErrors.messages[keyword] = message;
    };

    if (!errors || errors.length === 0) {
      return result;
    }

    for (const error of errors) {
      const path = this.normalizeConfigTreeInstancePath(error.instancePath);
      addError(
        path,
        error.parentSchema as SchemaDefinition,
        error.data as JSONValue,
        error.keyword,
        error.message || '',
      );

      // AJV reports `required` on the containing object; the UI needs a marker on the missing leaf node.
      if (error.keyword === 'required' && error.params?.missingProperty) {
        const missing = String(error.params.missingProperty);
        if (engine === 'cfworker') {
          // cfworker may already return expanded required errors with `instancePath` pointing to the leaf.
          // Avoid creating a bogus descendant like `/aValue/aValue`, which would hide the marker on `/aValue`.
          if (String(error.instancePath ?? '').endsWith(`/${missing}`)) {
            continue;
          }
        }
        const fieldPath = this.joinInstancePathWithSegment(error.instancePath, missing);
        addError(fieldPath, error.parentSchema as SchemaDefinition, error.data as JSONValue, error.keyword, 'required');
      }

      // Same for `dependentRequired`: attach the error to the missing property path so the leaf row is highlighted.
      if (error.keyword === 'dependentRequired' && error.params?.missingProperty) {
        const missing = String(error.params.missingProperty);
        if (engine === 'cfworker') {
          if (String(error.instancePath ?? '').endsWith(`/${missing}`)) {
            continue;
          }
        }
        const fieldPath = this.joinInstancePathWithSegment(error.instancePath, missing);
        addError(
          fieldPath,
          error.parentSchema as SchemaDefinition,
          error.data as JSONValue,
          error.keyword,
          error.message || '',
        );
      }
    }

    return result;
  }

  private filterConfigurationErrors(errors: ConfigurationErrors, attributes: ConfigurationAttributes) {
    // ignore errors for not active groups
    for (const [path, value] of Object.entries(attributes)) {
      if (value.isActive === false) {
        for (const [errorPath] of Object.entries(errors)) {
          if (errorPath === path || errorPath.startsWith(`${path}/`)) {
            delete errors[errorPath];
          }
        }
      }
    }

    for (const [errorPath, error] of Object.entries(errors)) {
      const fieldErrors = error as FieldErrors;
      const schema = fieldErrors.schema as SchemaDefinition;

      // Minimal unwrapping: if schema is nullable oneOf, prefer the non-null branch for type checks.
      const effectiveSchema =
        Array.isArray(schema.oneOf) && schema.oneOf.length === 2
          ? ((schema.oneOf.find((s) => (s as SchemaDefinition | undefined)?.type !== 'null') as SchemaDefinition) ??
            schema)
          : schema;

      if (effectiveSchema.type === 'string' && effectiveSchema.adcmMeta?.isSecret) {
        const fieldValue = fieldErrors.value as string;
        const isIgnoredKeyword =
          fieldErrors.messages.pattern || fieldErrors.messages.minLength || fieldErrors.messages.maxLength;

        // ignore hashed secrets from backend
        if (isIgnoredKeyword && fieldValue?.startsWith(secretFieldValuePrefixToIgnore)) {
          delete errors[errorPath];
        }
      }
    }
  }

  private fillParentPathParts(errors: ConfigurationErrors) {
    // root always has children with errors
    if (Object.keys(errors).length > 0) {
      if (!errors[rootNodeKey]) {
        errors[rootNodeKey] = true;
      }
    }

    // errorPath - is full path to field
    // like /configuration/cluster/clusterName
    for (const errorPath of Object.keys(errors)) {
      const parts = errorPath.split('/');
      let path = '';

      // skip first part and last:
      // - first part is empty string
      // - last part represents full path, and it already exists in errors
      for (let i = 1; i < parts.length - 1; i++) {
        const part = parts[i];
        path = `${path}/${part}`;

        if (!errors[path]) {
          errors[path] = true;
        } else {
          const parentError = errors[path];
          // if parent error already exists, add information about child errors
          if (typeof parentError === 'object') {
            parentError.messages[nestedPropsErrorKeyword] = nestedPropsErrorMessage;
          }
        }
      }
    }
  }
}

export const jsonSchemaValidationService = new JsonSchemaValidationService();

export const generateJsonSchemaDefaults = <T>(schema: SchemaLike): T | null | undefined =>
  jsonSchemaValidationService.generateDefaults<T>(DEFAULT_JSON_SCHEMA_ENGINE, schema);

import { type OutputUnit, type Schema, Validator } from '@cfworker/json-schema';
import { deepClone } from '@utils/objectUtils';

export type SchemaLike = Schema | object | boolean;

function isSchema(x: unknown): x is Schema {
  return typeof x === 'object' && x !== null;
}

export type ValidationError = {
  instancePath: string;
  parentSchema: Schema | undefined;
  data: unknown;
  keyword: string;
  message: string;
  params: Record<string, unknown>;
};

const KEYWORD_REQUIRED = 'required';
const KEYWORD_FALSE_SCHEMA = 'false-schema';
const KEYWORD_PATTERN = 'pattern';
const MESSAGE_FALSE_SCHEMA = 'Schema does not allow any value';
const MESSAGE_PATTERN_FALLBACK = 'pattern error';
const MESSAGE_REQUIRED = 'required';
const PROP_STATIC = 'static';
const ROOT_PATH_PATTERN = /^#?\//;
const HASH_PREFIX = /^#/;
const ARRAY_INDEX_PATTERN = /^\d+$/;

function getSchemaAtPath(schema: SchemaLike, instancePath: string): Schema | undefined {
  if (!isSchema(schema)) return undefined;
  if (!instancePath || instancePath === '/' || instancePath === '#') return schema;

  const parts = instancePath.replace(ROOT_PATH_PATTERN, '').split('/');
  let current: Schema | undefined = schema;

  for (const part of parts) {
    if (!current || !isSchema(current)) return undefined;

    const next: unknown = current.properties?.[part];
    if (isSchema(next)) {
      current = next;
      continue;
    }

    if (ARRAY_INDEX_PATTERN.test(part) && isSchema(current.items)) {
      current = current.items;
      continue;
    }

    return undefined;
  }

  return isSchema(current) ? current : undefined;
}

function runValidator<T>(schema: SchemaLike, data: T): { valid: boolean; errors: OutputUnit[] | undefined } {
  const schemaCopy: Schema = isSchema(schema) ? deepClone(schema) : (schema as unknown as Schema);
  const validator = new Validator(schemaCopy, undefined, false);
  return validator.validate(data);
}

/**
 * Aligns instance path with the schema path (keywordLocation).
 *
 * @cfworker/json-schema provides:
 * - instanceLocation: path to the value in the data
 * - keywordLocation: path to the keyword in the schema
 * These can diverge; we need the path to the specific field for config tree highlighting.
 *
 * Examples:
 * - instancePath: "/cluster", keywordLocation: "#/properties/cluster" → "/cluster" (unchanged)
 * - instancePath: "", keywordLocation: "#/properties/foo" → "/foo"
 * - instancePath: "/a", keywordLocation: "#/properties/a/properties/b" → "/a/b"
 */
function normalizeInstancePathFromKeywordLocation(instancePath: string, keywordLocation: string | undefined): string {
  if (!instancePath || !keywordLocation) return instancePath;

  const propertyMatch = /properties\/([^/]+)/g;
  let match: RegExpExecArray | null = null;
  let lastProperty: string | undefined;
  while ((match = propertyMatch.exec(keywordLocation)) !== null) {
    lastProperty = match[1];
  }
  if (lastProperty && !instancePath.endsWith(`/${lastProperty}`)) {
    return `${instancePath}/${lastProperty}`;
  }
  return instancePath;
}

function mapLibraryErrorsToValidationErrors<T>(
  errors: OutputUnit[],
  schema: SchemaLike,
  validatedData: T,
): ValidationError[] {
  const rootSchema: Schema | undefined = isSchema(schema) ? schema : undefined;

  return errors.map((err) => {
    const instancePath = err.instanceLocation?.replace(HASH_PREFIX, '') || '';
    const normalizedPath = normalizeInstancePathFromKeywordLocation(instancePath, err.keywordLocation);
    const parentSchema = getSchemaAtPath(schema, normalizedPath) ?? rootSchema;

    return {
      instancePath: normalizedPath,
      parentSchema,
      data: validatedData,
      keyword: err.keyword ?? '',
      message: err.error ?? '',
      params: {},
    };
  });
}

const NOISY_KEYWORDS = new Set(['properties', 'additionalProperties', 'items', 'false']);

function createValidationError(
  instancePath: string,
  parentSchema: Schema | undefined,
  data: unknown,
  keyword: string,
  message: string,
): ValidationError {
  return { instancePath, parentSchema, data, keyword, message, params: {} };
}

function filterNoisyKeywords(errors: ValidationError[]): ValidationError[] {
  return errors.filter((e) => !NOISY_KEYWORDS.has(e.keyword));
}

/**
 * Expands a single "required" error into one per missing property.
 * The library returns one error; the config tree needs per-field errors for highlighting.
 */
function expandRequiredErrors(errors: ValidationError[]): ValidationError[] {
  const result: ValidationError[] = [];

  for (const err of errors) {
    const requiredProps = err.parentSchema?.required;

    if (err.keyword === KEYWORD_REQUIRED && Array.isArray(requiredProps)) {
      const valueObj = (err.data as Record<string, unknown>) ?? {};
      for (const prop of requiredProps) {
        if (!(prop in valueObj)) {
          result.push({
            ...err,
            instancePath: `${err.instancePath}/${prop}`,
            keyword: KEYWORD_REQUIRED,
            message: MESSAGE_REQUIRED,
            params: { missingProperty: prop },
          });
        }
      }
    } else {
      result.push(err);
    }
  }

  return result;
}

export const validate = <T>(schema: SchemaLike, data: T): ValidationError[] | null => {
  if (schema === true) return null;

  if (schema === false) {
    return [createValidationError('', undefined, data, KEYWORD_FALSE_SCHEMA, MESSAGE_FALSE_SCHEMA)];
  }

  let libraryResult: { valid: boolean; errors: OutputUnit[] | undefined };
  try {
    libraryResult = runValidator(schema, data);
  } catch (e) {
    const rootSchema: Schema | undefined = isSchema(schema) ? schema : undefined;
    const message = e instanceof Error ? e.message : MESSAGE_PATTERN_FALLBACK;
    return [createValidationError('', rootSchema, data, KEYWORD_PATTERN, message)];
  }

  const { valid, errors } = libraryResult;
  if (valid || !errors || errors.length === 0) return null;

  const mapped = mapLibraryErrorsToValidationErrors(errors, schema, data);
  const filtered = filterNoisyKeywords(mapped);

  return expandRequiredErrors(filtered);
};

// =============================================================================
// Generation helpers
// =============================================================================

function getObjectDefault(schema: Schema): Record<string, unknown> {
  return schema.default && typeof schema.default === 'object'
    ? deepClone(schema.default as Record<string, unknown>)
    : {};
}

function isObjectSchema(s: Schema): boolean {
  return s.type === 'object' && s.properties != null && typeof s.properties === 'object';
}

function isArraySchema(s: Schema): boolean {
  return s.type === 'array' && s.items != null && isSchema(s.items);
}

/** Select oneOf branch by matching default with const in one of the branches. */
function selectOneOfBranchByConst(oneOfBranches: Schema[], defaultValues: Record<string, unknown>): Schema | undefined {
  for (const branch of oneOfBranches) {
    if (!branch.properties || typeof branch.properties !== 'object') continue;
    for (const [propName, propSchema] of Object.entries(branch.properties)) {
      if (
        isSchema(propSchema) &&
        'const' in propSchema &&
        propSchema.const !== undefined &&
        defaultValues[propName] === propSchema.const
      ) {
        return branch;
      }
    }
  }
  return undefined;
}

/** Select oneOf branch that has default, otherwise the first one. */
function selectOneOfBranchByDefault(oneOfBranches: Schema[]): Schema {
  const withDefault = oneOfBranches.find((b) => b.default !== undefined);
  return withDefault ?? oneOfBranches[0];
}

function getStaticSubSchemaFromBranch(branch: Schema): Schema | undefined {
  const sub = branch.properties?.[PROP_STATIC];
  return isSchema(sub) ? sub : undefined;
}

/**
 * Fills result.static when generating defaults for oneOf schemas (e.g. with discriminator).
 * ADCM config may have "dynamic" and "static" branches; "static" has its own sub-schema with default.
 */
function ensureStaticInResult(
  result: Record<string, unknown>,
  oneOfBranches: Schema[],
  selectedBranch: Schema | undefined,
): void {
  if (result[PROP_STATIC] !== undefined) return;

  if (selectedBranch) {
    const staticSchema = getStaticSubSchemaFromBranch(selectedBranch);
    if (staticSchema?.default !== undefined) {
      result[PROP_STATIC] = deepClone(staticSchema.default);
      return;
    }
  }

  const branchWithStatic = oneOfBranches.find((b) => isSchema(b) && b.properties?.[PROP_STATIC] != null);
  const staticSchema = branchWithStatic && getStaticSubSchemaFromBranch(branchWithStatic);
  if (!staticSchema) return;

  if (staticSchema.default !== undefined) {
    result[PROP_STATIC] = deepClone(staticSchema.default);
  } else {
    const generated = generateFromSchema(staticSchema);
    if (generated !== undefined) result[PROP_STATIC] = generated;
  }
}

/** Add defaults from all oneOf branches for fields not yet present in result. */
function applyDefaultsFromOneOfBranches(result: Record<string, unknown>, oneOfBranches: Schema[]): void {
  for (const branch of oneOfBranches) {
    if (!branch.properties || typeof branch.properties !== 'object') continue;
    for (const [propName, propSchema] of Object.entries(branch.properties)) {
      if (isSchema(propSchema) && propSchema.default !== undefined && result[propName] === undefined) {
        result[propName] = deepClone(propSchema.default);
      }
    }
  }
}

/** oneOf when type !== 'object': merge root default with the selected branch. */
function generateFromOneOfNonObject<T>(schema: Schema): T | undefined {
  const oneOf = schema.oneOf;
  if (!Array.isArray(oneOf) || oneOf.length === 0) return undefined;

  const base = schema.default !== undefined ? deepClone(schema.default as T) : undefined;
  const selected = selectOneOfBranchByDefault(oneOf);
  const branch = generateFromSchema<T>(selected);

  if (branch && typeof branch === 'object' && base && typeof base === 'object') {
    return { ...(base as object), ...(branch as object) } as T;
  }
  return (branch ?? base) as T | undefined;
}

/** Object with oneOf (incl. discriminator): select branch by const/default, fill static and defaults. */
function generateFromObjectWithOneOf<T>(schema: Schema): T {
  const result: Record<string, unknown> =
    schema.default && typeof schema.default === 'object' ? deepClone(schema.default as Record<string, unknown>) : {};

  const oneOf = schema.oneOf!;
  const selectedByConst = selectOneOfBranchByConst(oneOf, result as Record<string, unknown>);
  const selected = selectedByConst ?? selectOneOfBranchByDefault(oneOf) ?? oneOf[0];

  const branchValue = generateFromSchema<T>(selected);
  if (branchValue && typeof branchValue === 'object') Object.assign(result, branchValue);

  ensureStaticInResult(result, oneOf, selected);
  applyDefaultsFromOneOfBranches(result, oneOf);

  return result as T;
}

/** Plain object without oneOf: generate from properties recursively, add static for oneOf fields if needed. */
function generateFromObjectProperties<T>(schema: Schema): T {
  const result = getObjectDefault(schema);

  for (const [key, propSchema] of Object.entries(schema.properties!)) {
    if (!isSchema(propSchema) || result[key] !== undefined) continue;

    const value = generateFromSchema(propSchema);

    if (
      value &&
      typeof value === 'object' &&
      Array.isArray(propSchema.oneOf) &&
      (value as Record<string, unknown>)[PROP_STATIC] === undefined
    ) {
      const branchWithStatic = propSchema.oneOf.find((o) => isSchema(o) && o.properties?.[PROP_STATIC] != null);
      const staticSchema = branchWithStatic && getStaticSubSchemaFromBranch(branchWithStatic);
      if (staticSchema?.default !== undefined) {
        (value as Record<string, unknown>)[PROP_STATIC] = deepClone(staticSchema.default);
      }
    }

    if (value !== null && value !== undefined) result[key] = value;
  }

  return result as T;
}

function generateFromArray<T>(schema: Schema): T | undefined {
  if (!isSchema(schema.items)) return undefined;
  const item = generateFromSchema(schema.items);

  return (item != null ? [item] : []) as unknown as T;
}

export const generateFromSchema = <T>(schema: SchemaLike): T | undefined => {
  if (!isSchema(schema)) return undefined;

  if (schema.default === null) return null as T;

  // oneOf without type: 'object' — e.g. type variants or null
  if (schema.type !== 'object' && Array.isArray(schema.oneOf) && schema.oneOf.length > 0) {
    return generateFromOneOfNonObject<T>(schema);
  }

  if (isObjectSchema(schema)) {
    if (Array.isArray(schema.oneOf) && schema.oneOf.length > 0) {
      return generateFromObjectWithOneOf<T>(schema);
    }
    return generateFromObjectProperties<T>(schema);
  }

  if (isArraySchema(schema)) {
    return generateFromArray<T>(schema);
  }

  if (schema.default !== undefined) {
    return deepClone(schema.default as T);
  }

  return undefined;
};

export const getPatternErrorMessage = (pattern: string) => `The value must match pattern: ${pattern}`;

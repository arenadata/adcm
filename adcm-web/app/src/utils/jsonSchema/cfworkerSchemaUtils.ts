/**
 * CF Worker
 **/
import type { Schema } from '@cfworker/json-schema';
import { type OutputUnit, Validator } from '@cfworker/json-schema';
import { deepClone, getValueByPath } from '@utils/objectUtils';
export type SchemaLike = Schema | object | boolean;

function isSchema(x: unknown): x is Schema {
  // JSON Schema nodes are plain objects; arrays are used for keywords like `oneOf`/`anyOf` and must not be treated as schemas.
  return typeof x === 'object' && x !== null && !Array.isArray(x);
}

export type ValidationError = {
  instancePath: string;
  parentSchema: Schema | undefined;
  data: unknown;
  keyword: string;
  message: string;
  params: Record<string, unknown>;
};

const KEYWORDS = {
  required: 'required',
  dependentRequired: 'dependentRequired',
  oneOf: 'oneOf',
  falseSchema: 'false-schema',
  pattern: 'pattern',
  ref: '$ref',
  const: 'const',
  additionalProperties: 'additionalProperties',
  properties: 'properties',
  items: 'items',
  prefixItems: 'prefixItems',
  additionalItems: 'additionalItems',
  anyOf: 'anyOf',
  allOf: 'allOf',
  // biome-ignore lint/suspicious/noThenProperty: JSON Schema keyword `then`.
  then: 'then',
  else: 'else',
  if: 'if',
  false: 'false',
  type: 'type',
  enum: 'enum',
  minimum: 'minimum',
  maximum: 'maximum',
  exclusiveMinimum: 'exclusiveMinimum',
  exclusiveMaximum: 'exclusiveMaximum',
  multipleOf: 'multipleOf',
  minLength: 'minLength',
  maxLength: 'maxLength',
  minItems: 'minItems',
  maxItems: 'maxItems',
  minContains: 'minContains',
  maxContains: 'maxContains',
  contains: 'contains',
  uniqueItems: 'uniqueItems',
  minProperties: 'minProperties',
  maxProperties: 'maxProperties',
  unevaluatedProperties: 'unevaluatedProperties',
  unevaluatedItems: 'unevaluatedItems',
} as const;

const MESSAGE_FALSE_SCHEMA = 'Schema does not allow any value';
const MESSAGE_PATTERN_FALLBACK = 'pattern error';
const MESSAGE_REQUIRED = 'required';
const PROP_STATIC = 'static';
const ROOT_PATH_PATTERN = /^#?\//;
const HASH_PREFIX = /^#/;
const ARRAY_INDEX_PATTERN = /^\d+$/;

const KEYWORD_LOCATION_TERMINATORS = new Set<string>([
  // schema keywords (we want the parent schema that contains these keywords)
  KEYWORDS.required,
  KEYWORDS.type,
  KEYWORDS.const,
  KEYWORDS.enum,
  KEYWORDS.minimum,
  KEYWORDS.maximum,
  KEYWORDS.exclusiveMinimum,
  KEYWORDS.exclusiveMaximum,
  KEYWORDS.multipleOf,
  KEYWORDS.minLength,
  KEYWORDS.maxLength,
  KEYWORDS.pattern,
  KEYWORDS.minItems,
  KEYWORDS.maxItems,
  KEYWORDS.minContains,
  KEYWORDS.maxContains,
  KEYWORDS.uniqueItems,
  KEYWORDS.minProperties,
  KEYWORDS.maxProperties,
  KEYWORDS.additionalProperties,
  KEYWORDS.unevaluatedProperties,
  KEYWORDS.unevaluatedItems,
]);

// Split `keywordLocation` JSON pointer into path segments.
function parseKeywordLocationParts(keywordLocation: string): string[] {
  const pointer = keywordLocation.replace(HASH_PREFIX, '').replace(ROOT_PATH_PATTERN, '');
  return pointer ? pointer.split('/').filter(Boolean) : [];
}

// Step through schema tree for structural keywords (properties/items/oneOf/then/...).
function stepBySchemaKeyword(schema: Schema, part: string): unknown | undefined {
  switch (part) {
    case KEYWORDS.properties:
      return schema.properties;
    case KEYWORDS.items:
      return schema.items;
    case KEYWORDS.prefixItems:
      return schema.prefixItems;
    case KEYWORDS.oneOf:
      return schema.oneOf;
    case KEYWORDS.anyOf:
      return schema.anyOf;
    case KEYWORDS.allOf:
      return schema.allOf;
    case KEYWORDS.then:
      return schema.then;
    case KEYWORDS.else:
      return schema.else;
    case KEYWORDS.if:
      return schema.if;
    default:
      return undefined;
  }
}

// Read a value from root via a local JSON Pointer `#/...`.
function readByLocalJsonPointer(root: unknown, pointer: string): unknown {
  if (!pointer.startsWith('#')) return undefined;
  const path = pointer.replace(HASH_PREFIX, '');
  if (path === '' || path === '/') return root;
  return getValueByPath(root, path, '/');
}

// Resolve a local `$ref` like `#/...` against the root schema.
function resolveLocalRef(rootSchema: SchemaLike, ref: string): Schema | undefined {
  if (!isSchema(rootSchema)) return undefined;
  const resolved = readByLocalJsonPointer(rootSchema, ref);
  return isSchema(resolved) ? resolved : undefined;
}

// Return the schema node that *contains* the keyword addressed by `keywordLocation`.
function getSchemaAtKeywordLocation(schema: SchemaLike, keywordLocation: string | undefined): Schema | undefined {
  if (!isSchema(schema) || !keywordLocation) return undefined;

  // Examples:
  // - "#/properties/aValue/type"
  // - "#/then/required"
  // - "#/else/properties/x/minLength"
  const parts = parseKeywordLocationParts(keywordLocation);
  if (parts.length === 0) return schema;

  let current: unknown = schema;

  for (const part of parts) {
    // Keyword locations can traverse arrays, e.g. `#/properties/x/oneOf/0/required`.
    if (Array.isArray(current)) {
      if (ARRAY_INDEX_PATTERN.test(part)) {
        current = current[Number(part)];
        continue;
      }
      return undefined;
    }

    if (!isSchema(current)) return undefined;

    // If keywordLocation points to a concrete keyword (e.g. `#/then/required`),
    // we need the schema object that *contains* that keyword (here: `#/then`).
    if (KEYWORD_LOCATION_TERMINATORS.has(part)) return current;

    if (part === KEYWORDS.ref) {
      const ref = current[KEYWORDS.ref];
      if (typeof ref === 'string') {
        const resolved = resolveLocalRef(schema, ref);
        if (resolved) {
          current = resolved;
          continue;
        }
      }
      return current;
    }

    const byKeyword = stepBySchemaKeyword(current, part);
    if (byKeyword !== undefined) {
      current = byKeyword;
      continue;
    }

    const next = current[part];
    // If the pointer steps into a non-schema leaf (arrays/strings/etc), return the last schema we had.
    if (!isSchema(next)) return current;
    current = next;
  }

  return isSchema(current) ? current : undefined;
}

/** Value in `root` at JSON-pointer prefix (e.g. `/foo/bar`), or `root` when prefix is empty/root. */
function valueAtPath(root: unknown, instancePathPrefix: string): unknown {
  if (root === undefined) return undefined;
  if (instancePathPrefix === '' || instancePathPrefix === '/') return root;
  return getValueByPath(root, instancePathPrefix, '/');
}

/** Pick oneOf branch by comparing `instance[discriminator]` to each branch's const. */
function branchForDiscriminatedOneOf(schema: Schema, instance: unknown): Schema | undefined {
  const branches = schema.oneOf;
  const discName = getDiscriminatorPropertyName(schema);
  if (!Array.isArray(branches) || !discName) return undefined;
  if (instance === null || typeof instance !== 'object' || Array.isArray(instance)) return undefined;

  const instanceObj = instance as Record<string, unknown>;
  const value = instanceObj[discName];
  for (const b of branches) {
    if (!isSchema(b)) continue;
    const property = b.properties?.[discName];
    if (isSchema(property) && 'const' in property && property.const === value) return b;
  }
  return undefined;
}

/**
 * Walk schema by instance path. With `instanceRoot`, steps into the matching oneOf branch when the
 * current node uses `discriminator` (config tree paths under selection groups).
 */
function getSchemaAtPath(schema: SchemaLike, instancePath: string, instanceRoot?: unknown): Schema | undefined {
  if (!isSchema(schema)) return undefined;
  if (!instancePath || instancePath === '/' || instancePath === '#') return schema;

  const parts = instancePath.replace(ROOT_PATH_PATTERN, '').split('/').filter(Boolean);
  let current: Schema | undefined = schema;
  // Path to the JSON value that matches `current`; empty before the first segment.
  let instancePathPrefix = '';

  for (const part of parts) {
    if (!current || !isSchema(current)) return undefined;

    const prefixAfterThisPart = instancePathPrefix === '' ? `/${part}` : `${instancePathPrefix}/${part}`;
    let next: unknown = current.properties?.[part];

    if (!isSchema(next) && instanceRoot !== undefined) {
      const valueForCurrentSchema = valueAtPath(instanceRoot, instancePathPrefix);
      const branch = branchForDiscriminatedOneOf(current, valueForCurrentSchema);
      if (branch) next = branch.properties?.[part];
    }

    if (isSchema(next)) {
      current = next;
      instancePathPrefix = prefixAfterThisPart;
      continue;
    }

    if (ARRAY_INDEX_PATTERN.test(part) && isSchema(current.items)) {
      current = current.items;
      instancePathPrefix = prefixAfterThisPart;
      continue;
    }

    return undefined;
  }

  return isSchema(current) ? current : undefined;
}

// Read discriminator.propertyName from schema in a type-safe way.
function getDiscriminatorPropertyName(schema: Schema): string | undefined {
  const disc = schema.discriminator;
  if (!disc || typeof disc !== 'object' || Array.isArray(disc)) return undefined;
  const prop = (disc as { propertyName?: unknown }).propertyName;
  return typeof prop === 'string' && prop.length > 0 ? prop : undefined;
}

// Run cfworker Validator and return {valid, errors}.
function runValidator<T>(schema: SchemaLike, data: T): { valid: boolean; errors: OutputUnit[] | undefined } {
  const schemaCopy: Schema = isSchema(schema) ? deepClone(schema) : (schema as unknown as Schema);
  const validator = new Validator(schemaCopy, undefined, false);
  return validator.validate(data);
}

// Walk a schema tree and return the first non-null match returned by `visit`.
function walkSchemaFirstMatch<T>(root: Schema, visit: (node: Schema, root: Schema) => T | null): T | null {
  const visited = new WeakSet<object>();

  const stack: Schema[] = [root];
  while (stack.length > 0) {
    const node = stack.pop()!;
    if (visited.has(node)) continue;
    visited.add(node);

    const found = visit(node, root);
    if (found !== null) return found;

    for (const value of Object.values(node)) {
      if (Array.isArray(value)) {
        for (const v of value) {
          if (isSchema(v)) stack.push(v);
        }
      } else if (isSchema(value)) {
        stack.push(value);
      }
    }
  }

  return null;
}

/**
 * cfworker does not throw on broken local `$ref` the same way AJV does on compilation.
 * To align behavior, we pre-scan the schema for local refs and return a synthetic root `$ref` error
 * when the pointer cannot be resolved.
 */
function findFirstBrokenLocalRef(schema: SchemaLike): string | null {
  if (!isSchema(schema)) return null;

  return walkSchemaFirstMatch(schema, (node, root) => {
    const ref = node.$ref;
    if (typeof ref === 'string' && ref.startsWith('#/')) {
      const resolved = readByLocalJsonPointer(root, ref);
      if (resolved === undefined) return ref;
    }
    return null;
  });
}

/**
 * AJV (strict mode) rejects unknown keywords. cfworker is more permissive and may silently ignore them,
 * which would make validation "pass" when AJV fails at compile-time.
 *
 * For our engine-comparison stories we treat AJV as gold standard, so we pre-scan for keywords that are
 * not valid in draft 2020-12 (e.g. `additionalItems`) and return a synthetic compilation error.
 */
function findFirstUnsupportedKeyword(schema: SchemaLike): string | null {
  if (!isSchema(schema)) return null;

  return walkSchemaFirstMatch(schema, (node) =>
    Object.hasOwn(node, KEYWORDS.additionalItems) ? KEYWORDS.additionalItems : null,
  );
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
 * - instancePath: "/cfg/cluster/0", keywordLocation: ".../properties/cluster/items/required" → unchanged (do not append `cluster`)
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
    const segments = instancePath.split('/').filter(Boolean);
    const lastSeg = segments.at(-1);
    const prevSeg = segments.at(-2);
    // the last `properties` segment is then the array field name
    // while `instancePath` is already `/.../cluster/<index>`. Appending
    // `cluster` again would break leaf paths and tree error highlighting.
    if (lastSeg && ARRAY_INDEX_PATTERN.test(lastSeg) && prevSeg === lastProperty) {
      return instancePath;
    }
    return `${instancePath}/${lastProperty}`;
  }
  return instancePath;
}

function mapLibraryErrorsToValidationErrors(
  errors: OutputUnit[],
  schema: SchemaLike,
  validatedData: unknown,
): ValidationError[] {
  const rootSchema: Schema | undefined = isSchema(schema) ? schema : undefined;

  return errors.map((err) => {
    const instancePath = err.instanceLocation?.replace(HASH_PREFIX, '') || '';
    const isPropertyNamesSubKeyword = Boolean(err.keywordLocation?.startsWith('#/propertyNames/'));
    // `propertyNames` validates *object keys*, so AJV attaches those errors to the object itself (instancePath: "").
    // cfworker reports instanceLocation like "#/badKey". Keep AJV-like behavior for tree highlighting.
    const normalizedPath = isPropertyNamesSubKeyword
      ? ''
      : normalizeInstancePathFromKeywordLocation(instancePath, err.keywordLocation);
    const schemaFromKeywordLocation = getSchemaAtKeywordLocation(schema, err.keywordLocation);
    const parentSchema =
      schemaFromKeywordLocation ?? getSchemaAtPath(schema, normalizedPath, validatedData) ?? rootSchema;
    // Fast path: cfworker often reports root location (`#` → ""), especially for applicator keywords like `if/then`.
    // Avoid an extra pointer traversal when we already know it's the root value.
    const data =
      normalizedPath === '' || normalizedPath === '/'
        ? validatedData
        : getValueByPath(validatedData, normalizedPath, '/');
    const message = err.error ?? '';
    const parentPattern = isSchema(parentSchema) ? parentSchema.pattern : undefined;

    const keyword = err.keyword === KEYWORDS.false ? KEYWORDS.falseSchema : (err.keyword ?? '');
    const additionalProp = keyword === KEYWORDS.additionalProperties ? extractAdditionalPropertyName(message) : null;
    const unevaluatedProp = keyword === KEYWORDS.unevaluatedProperties ? extractAdditionalPropertyName(message) : null;
    const propertyName =
      err.keyword === KEYWORDS.pattern && isPropertyNamesSubKeyword
        ? (instancePath.split('/').filter(Boolean).at(-1) ?? null)
        : null;

    const isPatternError = err.keyword === KEYWORDS.pattern && typeof parentPattern === 'string';

    let finalMessage = message;
    if (isPatternError) {
      finalMessage = `must match pattern "${parentPattern}"`;
    } else if (CFWORKER_LIBRARY_NOISE_MESSAGES.some((re) => re.test(message))) {
      finalMessage = '';
    }

    let params: Record<string, unknown> = {};
    if (isPatternError) {
      params = { pattern: parentPattern };
      if (propertyName) params.propertyName = propertyName;
    } else if (additionalProp) {
      params = { additionalProperty: additionalProp };
    } else if (unevaluatedProp) {
      params = { unevaluatedProperty: unevaluatedProp };
    }

    return {
      instancePath: normalizedPath,
      parentSchema,
      data,
      keyword,
      message: finalMessage,
      params,
    };
  });
}

// `properties` is usually a library-level wrapper/noise for our UI.
const CFWORKER_LIBRARY_NOISE_KEYWORDS = new Set<string>([KEYWORDS.properties]);

const CFWORKER_LIBRARY_NOISE_MESSAGES = [
  // cfworker can emit aggregate applicator failures in addition to the concrete leaf errors.
  // These messages add noise in the UI tooltips and do not help identify the actual failing constraint.
  /^Instance does not match every subschema\.?$/i,
];

// Errors produced when cfworker tries to validate object-only branches against a `null` value.
// If the schema at the instance path allows `null`, AJV treats the value as valid and does not emit these.
const CFWORKER_NULL_TOLERANT_KEYWORDS = new Set<string>([
  KEYWORDS.oneOf,
  KEYWORDS.type,
  KEYWORDS.required,
  KEYWORDS.const,
  KEYWORDS.additionalProperties,
  KEYWORDS.falseSchema,
]);

// Create a normalized ValidationError object (internal helper).
function createValidationError(
  instancePath: string,
  parentSchema: Schema | undefined,
  data: unknown,
  keyword: string,
  message: string,
): ValidationError {
  return { instancePath, parentSchema, data, keyword, message, params: {} };
}

// Return true if `prop` is allowed by `properties` or `patternProperties` on the parent schema.
function isPropertyAllowedByParentSchema(parentSchema: Schema, prop: string): boolean {
  const properties = parentSchema.properties;
  if (properties && typeof properties === 'object' && Object.hasOwn(properties, prop)) {
    return true;
  }

  const patternProperties = parentSchema.patternProperties;
  if (patternProperties && typeof patternProperties === 'object') {
    for (const pattern of Object.keys(patternProperties)) {
      try {
        if (new RegExp(pattern).test(prop)) return true;
      } catch {
        // ignore invalid regexes in schema
      }
    }
  }

  return false;
}

// Prune cfworker noise and enforce AJV-like UI policy.
function pruneCfworkerLibraryNoise(errors: ValidationError[]): ValidationError[] {
  const withoutKeywords = errors.filter((e) => !CFWORKER_LIBRARY_NOISE_KEYWORDS.has(String(e.keyword)));

  const extraPropLeafPathsToDrop = new Set<string>();
  const unevaluatedPropLeafPathsToDrop = new Set<string>();

  // cfworker sometimes reports a root-level additionalProperties error like
  // `Property "arr" does not match additional properties schema.` when a property itself is invalid.
  // If we already have any error attached to that property path, drop the wrapper error to avoid highlighting the root.
  const hasErrorAtPath = new Set<string>(withoutKeywords.map((e) => e.instancePath));
  const withoutAdditionalPropsWrappers = withoutKeywords.filter((e) => {
    if (e.keyword !== KEYWORDS.additionalProperties) return true;
    const prop = extractAdditionalPropertyName(e.message);
    if (!prop) return true;
    const childPath = e.instancePath === '' ? `/${prop}` : `${e.instancePath}/${prop}`;

    // If the property is NOT allowed by schema (additionalProperties:false and not in properties/patternProperties),
    // this is a real "extra key" violation. Keep the object-level marker (AJV behavior) and drop leaf false-schema noise.
    if (
      isSchema(e.parentSchema) &&
      e.parentSchema.additionalProperties === false &&
      !isPropertyAllowedByParentSchema(e.parentSchema, prop)
    ) {
      extraPropLeafPathsToDrop.add(childPath);
      return true;
    }

    if (hasErrorAtPath.has(childPath)) return false;
    // Also drop if we have any descendant error for that property.
    for (const p of hasErrorAtPath) {
      if (isStrictDescendantPath(childPath, p)) return false;
    }
    return true;
  });

  // `unevaluatedProperties:false` is similar to `additionalProperties:false`: AJV marks the object,
  // while cfworker can additionally emit a leaf `false-schema` at `/prop`. Drop that leaf noise.
  for (const e of withoutAdditionalPropsWrappers) {
    if (e.keyword !== KEYWORDS.unevaluatedProperties) continue;
    const prop = extractAdditionalPropertyName(e.message);
    if (!prop) continue;
    if (isSchema(e.parentSchema) && e.parentSchema.unevaluatedProperties === false) {
      const childPath = e.instancePath === '' ? `/${prop}` : `${e.instancePath}/${prop}`;
      unevaluatedPropLeafPathsToDrop.add(childPath);
    }
  }

  // For real additionalProperties:false violations, drop the leaf boolean-schema noise on `/prop`.
  const withoutExtraPropLeafNoise = withoutAdditionalPropsWrappers.filter((e) => {
    if (e.keyword !== KEYWORDS.falseSchema) return true;
    const dropByAdditional = [...extraPropLeafPathsToDrop].some(
      (p) => e.instancePath === p || isStrictDescendantPath(p, e.instancePath),
    );
    if (dropByAdditional) return false;
    const dropByUnevaluated = [...unevaluatedPropLeafPathsToDrop].some(
      (p) => e.instancePath === p || isStrictDescendantPath(p, e.instancePath),
    );
    return !dropByUnevaluated;
  });

  // cfworker can emit `false` (mapped to `false-schema`) as a generic wrapper on ancestor objects
  // when a descendant constraint fails (e.g. `minLength` in a deep leaf). AJV does not surface those,
  // and keeping them breaks "inactive group" suppression by leaving errors on ancestors.
  //
  // Drop `false-schema` at a path if there exists any *concrete* descendant error under that path.
  const concretePaths = withoutExtraPropLeafNoise
    .filter((e) => e.keyword !== KEYWORDS.falseSchema)
    .map((e) => e.instancePath);
  const concreteAtSamePath = new Set(concretePaths);

  const withoutFalseSchemaWrappers = withoutExtraPropLeafNoise.filter((e) => {
    if (e.keyword !== KEYWORDS.falseSchema) return true;
    // If there is a concrete error on the same path, `false-schema` only adds noisy duplication.
    if (concreteAtSamePath.has(e.instancePath)) return false;
    return !concretePaths.some((p) => isStrictDescendantPath(e.instancePath, p));
  });

  // cfworker can emit `$ref: A subschema had errors.` alongside more specific errors at the same path.
  // Drop `$ref` when we have any other keyword for the same instancePath.
  const hasMoreSpecificAtPath = new Set<string>();
  for (const e of withoutFalseSchemaWrappers) {
    if (e.keyword !== KEYWORDS.ref) {
      hasMoreSpecificAtPath.add(e.instancePath);
    }
  }

  return withoutFalseSchemaWrappers.filter(
    (e) => !(e.keyword === KEYWORDS.ref && hasMoreSpecificAtPath.has(e.instancePath)),
  );
}

// Normalize `items:false` (tuple vs disallow-any) to match AJV highlighting.
function normalizeItemsFalseErrors(
  errors: ValidationError[],
  rootSchema: SchemaLike,
  rootData: unknown,
): ValidationError[] {
  const itemsErrors = errors.filter((e) => e.keyword === KEYWORDS.items);
  if (itemsErrors.length === 0) return errors;

  let result = [...errors];

  for (const itemsErr of itemsErrors) {
    const schemaAtPath = getSchemaAtPath(rootSchema, itemsErr.instancePath, rootData);
    if (!isSchema(schemaAtPath)) continue;

    const items = schemaAtPath.items;
    if (items !== false) continue;

    const prefixItems = schemaAtPath.prefixItems;
    const prefixLen = Array.isArray(prefixItems) ? prefixItems.length : 0;
    const value = valueAtPath(rootData, itemsErr.instancePath);
    if (!Array.isArray(value)) continue;

    if (prefixLen > 0) {
      // Tuple arrays with `items:false`: AJV highlights the array-level `items` constraint, not the leaf boolean-schema errors.
      result = result.filter(
        (e) => !(e.keyword === KEYWORDS.falseSchema && isStrictDescendantPath(itemsErr.instancePath, e.instancePath)),
      );
    } else {
      // `items:false` disallow-any: AJV highlights the offending items.
      // Drop the array-level wrapper and keep leaf `false schema` markers.
      if (value.length > 0) {
        result = result.filter((e) => !(e.keyword === KEYWORDS.items && e.instancePath === itemsErr.instancePath));
      }
      // cfworker may also emit a container-level `false` at the array path itself (`#/arr`).
      // For disallow-any we want leaf markers only.
      result = result.filter((e) => !(e.keyword === KEYWORDS.falseSchema && e.instancePath === itemsErr.instancePath));
    }
  }

  return result;
}

// Normalize `unevaluatedItems:false`: keep array-level marker and drop leaf `false-schema` noise.
function normalizeUnevaluatedItemsFalseErrors(
  errors: ValidationError[],
  rootSchema: SchemaLike,
  rootData: unknown,
): ValidationError[] {
  const unevaluatedErrors = errors.filter((e) => e.keyword === KEYWORDS.unevaluatedItems);
  if (unevaluatedErrors.length === 0) return errors;

  let result = [...errors];

  for (const uErr of unevaluatedErrors) {
    const schemaAtPath = getSchemaAtPath(rootSchema, uErr.instancePath, rootData);
    if (!isSchema(schemaAtPath)) continue;

    const unevaluated = schemaAtPath.unevaluatedItems;
    if (unevaluated !== false) continue;

    // AJV highlights `unevaluatedItems` on the array. cfworker may additionally emit `false schema`
    // for the unevaluated elements and even for the array itself drop those to keep the same UI marker.
    result = result.filter((e) => {
      if (e.keyword !== KEYWORDS.falseSchema) return true;
      if (e.instancePath === uErr.instancePath) return false;
      return !isStrictDescendantPath(uErr.instancePath, e.instancePath);
    });
  }

  return result;
}

// Check if schema explicitly allows `null` (type: "null" or type includes "null").
function schemaAllowsNull(schema: Schema | undefined): boolean {
  if (!schema) return false;
  const t = schema.type;
  if (t === 'null') return true;
  if (Array.isArray(t)) return t.includes('null');
  return false;
}

/**
 * cfworker sometimes validates `oneOf` even when `type` allows `null` (e.g. `type: ['object','null']`).
 * AJV treats such values as valid and does not evaluate discriminator/oneOf branches.
 *
 * To align behavior, drop errors that are solely caused by evaluating object-only constraints on a `null` value
 * when the schema explicitly allows `null`.
 */
function dropErrorsForAllowedNullValues(
  errors: ValidationError[],
  rootSchema: SchemaLike,
  rootData: unknown,
): ValidationError[] {
  return errors.filter((e) => {
    // If the runtime value at this path is `null`, and the schema-at-path explicitly allows `null`,
    // then any object-branch errors emitted by cfworker for this path are noise (AJV treats it as valid).
    const valueAtInstance = valueAtPath(rootData, e.instancePath);
    if (valueAtInstance === null) {
      const schemaAtPath = getSchemaAtPath(rootSchema, e.instancePath, rootData);
      if (schemaAllowsNull(schemaAtPath) && CFWORKER_NULL_TOLERANT_KEYWORDS.has(e.keyword)) {
        return false;
      }
    }

    // Drop parent additionalProperties errors that only exist because a nullable child is `null`.
    if (e.keyword === KEYWORDS.additionalProperties) {
      const prop = extractAdditionalPropertyName(e.message);
      if (!prop) return true;
      const childPath = e.instancePath === '' ? `/${prop}` : `${e.instancePath}/${prop}`;
      const childValue = valueAtPath(rootData, childPath);
      if (childValue !== null) return true;

      const childSchema = getSchemaAtPath(rootSchema, childPath, rootData);
      if (schemaAllowsNull(childSchema)) {
        return false;
      }
    }

    return true;
  });
}

// Join two JSON-pointer-like path fragments.
function joinJsonPointerPath(prefix: string, suffix: string): string {
  if (!suffix) return prefix;
  if (suffix === '/') return prefix || '/';
  if (suffix.startsWith('/')) return `${prefix}${suffix}`;
  return `${prefix}/${suffix}`;
}

/**
 * cfworker reports `contains` as an aggregate array-level error.
 * For better UX (and to match AJV output), emit element-level errors by validating each item against the `contains` schema.
 */
function enrichContainsErrors(errors: ValidationError[], rootSchema: SchemaLike, rootData: unknown): ValidationError[] {
  const containsErrors = errors.filter((e) => e.keyword === KEYWORDS.contains);
  if (containsErrors.length === 0) return errors;

  const result: ValidationError[] = [...errors];

  for (const err of containsErrors) {
    const schemaAtPath = getSchemaAtPath(rootSchema, err.instancePath, rootData);
    if (!schemaAtPath || !isSchema(schemaAtPath)) continue;

    const containsSchema = schemaAtPath.contains;
    if (!isSchema(containsSchema)) continue;

    const value = valueAtPath(rootData, err.instancePath);
    if (!Array.isArray(value)) continue;

    for (let i = 0; i < value.length; i++) {
      const item = value[i];
      // Validate item against contains schema and attach the first error to `/path/<i>`.
      const lib = validateWithCfWorkerLibrary(containsSchema, item);
      if (!lib || lib.length === 0) continue;
      const mapped = mapLibraryErrorsToValidationErrors(lib, containsSchema, item);
      const first = mapped.find((e) => e.keyword !== KEYWORDS.false) ?? mapped[0];
      if (!first) continue;

      const itemPath = `${err.instancePath}/${i}`;
      result.push({
        ...first,
        instancePath: joinJsonPointerPath(itemPath, first.instancePath),
      });
    }
  }

  return result;
}

// Check if schema type includes `array` (including union types).
function schemaHasArrayType(schema: SchemaLike): boolean {
  if (!isSchema(schema)) return false;
  const t = schema.type;
  if (t === 'array') return true;
  if (Array.isArray(t)) return t.includes('array');
  return false;
}

// Post-check for `contains` constraints (cfworker may report valid when AJV would fail).
function collectContainsConstraintErrors(schema: SchemaLike, data: unknown, instancePath = ''): ValidationError[] {
  if (!isSchema(schema)) return [];

  const result: ValidationError[] = [];

  // Check current node for contains constraints on arrays.
  if (schemaHasArrayType(schema) && schema.contains !== undefined) {
    const containsSchema = schema.contains;
    if (isSchema(containsSchema) && Array.isArray(data)) {
      const min = Number(schema.minContains ?? 1);
      const maxRaw = schema.maxContains;
      const max = maxRaw === undefined ? Number.POSITIVE_INFINITY : Number(maxRaw);

      let validCount = 0;
      for (const item of data) {
        const libErrors = validateWithCfWorkerLibrary(containsSchema, item);
        if (!libErrors || libErrors.length === 0) validCount++;
      }

      if (validCount < min || validCount > max) {
        result.push({
          ...createValidationError(
            instancePath,
            containsSchema,
            data,
            KEYWORDS.contains,
            'Array does not contain item matching schema.',
          ),
          params: { minContains: min, ...(Number.isFinite(max) ? { maxContains: max } : {}) },
        });
      }
    }
  }

  // Recurse into objects.
  if (
    data &&
    typeof data === 'object' &&
    !Array.isArray(data) &&
    schema.properties &&
    typeof schema.properties === 'object'
  ) {
    const obj = data as Record<string, unknown>;
    for (const [k, childSchema] of Object.entries(schema.properties)) {
      if (!Object.hasOwn(data, k)) continue;
      result.push(...collectContainsConstraintErrors(childSchema, obj[k], `${instancePath}/${k}`));
    }
  }

  // Recurse into arrays (items / prefixItems).
  if (Array.isArray(data)) {
    const prefixItems = schema.prefixItems;
    if (Array.isArray(prefixItems)) {
      for (let i = 0; i < Math.min(prefixItems.length, data.length); i++) {
        result.push(...collectContainsConstraintErrors(prefixItems[i], data[i], `${instancePath}/${i}`));
      }
    }

    const items = schema.items;
    if (items !== undefined) {
      for (let i = 0; i < data.length; i++) {
        result.push(...collectContainsConstraintErrors(items, data[i], `${instancePath}/${i}`));
      }
    }
  }

  return result;
}

// Return true if `path` is a strict descendant of `ancestor`.
function isStrictDescendantPath(ancestor: string, path: string): boolean {
  if (ancestor === '') {
    return path !== '' && path.startsWith('/');
  }
  return path.startsWith(`${ancestor}/`);
}

// Return `v` as a plain object record, or null if it's not an object.
function asPlainObjectRecord(v: unknown): Record<string, unknown> | null {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
}

/**
 * Enrichment step: reconstruct missingProperty/leaf errors for object-shaped keywords that cfworker
 * reports at container level.
 */
function enrichMissingPropertyErrors(errors: ValidationError[]): ValidationError[] {
  const result: ValidationError[] = [];

  for (const err of errors) {
    // `required`: expand to one error per missing property for leaf highlighting.
    const parentSchema = err.parentSchema;
    if (err.keyword === KEYWORDS.required && parentSchema && Array.isArray(parentSchema.required)) {
      const requiredProps = parentSchema.required;
      const valueObj = asPlainObjectRecord(err.data) ?? {};
      let didExpand = false;

      for (const prop of requiredProps) {
        if (prop in valueObj) continue;
        didExpand = true;
        result.push({
          ...err,
          instancePath: `${err.instancePath}/${prop}`,
          keyword: KEYWORDS.required,
          message: MESSAGE_REQUIRED,
          params: { missingProperty: prop },
        });
      }

      if (!didExpand) result.push(err);
      continue;
    }

    // `dependentRequired`: expand to one error per missing dependency for leaf highlighting.
    if (err.keyword === KEYWORDS.dependentRequired && parentSchema?.dependentRequired) {
      const deps = parentSchema.dependentRequired;
      const valueObj = asPlainObjectRecord(err.data) ?? {};
      let didExpand = false;

      if (deps && typeof deps === 'object') {
        for (const [triggerProp, requiredProps] of Object.entries(deps)) {
          if (!(triggerProp in valueObj)) continue;
          if (!Array.isArray(requiredProps)) continue;

          for (const missingProp of requiredProps) {
            if (missingProp in valueObj) continue;
            didExpand = true;
            result.push({
              ...err,
              instancePath: `${err.instancePath}/${missingProp}`,
              keyword: KEYWORDS.dependentRequired,
              params: { ...(err.params ?? {}), property: triggerProp, missingProperty: missingProp },
            });
          }
        }
      }

      if (!didExpand) result.push(err);
      continue;
    }

    result.push(err);
  }

  return result;
}

/**
 * cfworker message format: "Property \"text\" does not match additional properties schema."`
 * We need the property name (`text`) to decide whether the error belongs to the selected discriminator branch.
 */
function extractAdditionalPropertyName(message: string): string | null {
  // cfworker embeds the property name into the message; there is no structured field for it.
  const m = /Property "([^"]+)"/.exec(message);
  return m?.[1] ?? null;
}

type DiscriminatedCtx = {
  path: string;
  discName: string;
  discValue: string;
  selectionKind: 'known' | 'missing_or_unknown';
  selectedBranchProps: Set<string>;
};

// Find discriminator context for a oneOf error (selected branch, discriminator name/value, etc.).
function findDiscriminatorContextForOneOfError(oneOfError: ValidationError): DiscriminatedCtx | null {
  const schema = oneOfError.parentSchema;
  if (!isSchema(schema)) return null;

  const discName = getDiscriminatorPropertyName(schema);
  if (!discName) return null;

  const value = oneOfError.data;
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return {
      path: oneOfError.instancePath,
      discName,
      discValue: '',
      selectionKind: 'missing_or_unknown',
      selectedBranchProps: new Set(),
    };
  }

  const valueObj = value as Record<string, unknown>;
  const discValue = valueObj[discName];
  if (typeof discValue !== 'string') {
    return {
      path: oneOfError.instancePath,
      discName,
      discValue: '',
      selectionKind: 'missing_or_unknown',
      selectedBranchProps: new Set(),
    };
  }

  const branches = schema.oneOf;
  if (!Array.isArray(branches)) return null;

  const selected = branches.find((b): b is Schema => {
    if (!isSchema(b)) return false;
    const prop = b.properties?.[discName];
    return isSchema(prop) && 'const' in prop && prop.const === discValue;
  });
  if (!selected) {
    return {
      path: oneOfError.instancePath,
      discName,
      discValue,
      selectionKind: 'missing_or_unknown',
      selectedBranchProps: new Set(),
    };
  }

  const props = selected.properties ? Object.keys(selected.properties) : [];
  return {
    path: oneOfError.instancePath,
    discName,
    discValue,
    selectionKind: 'known',
    selectedBranchProps: new Set(props),
  };
}

/**
 * Discriminator-union normalization (cfworker):
 *
 * cfworker validates discriminator-based unions via plain oneOf and can emit errors from non-selected branches.
 * We apply two policies:
 * - **Branch restriction**: when selection is known, drop errors that belong only to other branches.
 * - **Marker visibility**: when selection is missing/unknown, keep parent oneOf marker and drop descendants that would hide it.
 */
function normalizeDiscriminatorOneOfErrors(errors: ValidationError[]): ValidationError[] {
  const oneOfErrors = errors.filter((e) => e.keyword === KEYWORDS.oneOf);
  if (oneOfErrors.length === 0) return errors;

  const contexts: DiscriminatedCtx[] = oneOfErrors
    .map(findDiscriminatorContextForOneOfError)
    .filter((x): x is DiscriminatedCtx => x !== null);

  if (contexts.length === 0) return errors;
  const contextByPath = new Map<string, DiscriminatedCtx>(contexts.map((c) => [c.path, c]));
  const knownContexts = contexts.filter((c) => c.selectionKind === 'known');

  // 1) Branch restriction (selection known): drop errors from non-selected branches.
  const branchRestricted = errors.filter((e) => {
    for (const ctx of knownContexts) {
      if (!isStrictDescendantPath(ctx.path, e.instancePath) && e.instancePath !== ctx.path) continue;

      // Drop discriminator const mismatches from non-selected branches.
      if (e.keyword === KEYWORDS.const && e.instancePath === `${ctx.path}/${ctx.discName}`) {
        const ps = e.parentSchema;
        if (isSchema(ps) && 'const' in ps && ps.const !== ctx.discValue) return false;
      }

      // Drop required leaf errors that are not part of the selected branch.
      if (e.keyword === KEYWORDS.required && e.params?.missingProperty) {
        const missingProp = String(e.params.missingProperty);
        // Only apply this pruning to container-level required errors produced by non-selected branches
        // (e.g. `/variant` missing `num` while `_selection` is `str`). For nested required errors
        // (e.g. `/variant/cfg` missing `enabled`) the selected branch top-level properties are irrelevant.
        if (e.instancePath === ctx.path && !ctx.selectedBranchProps.has(missingProp)) return false;
      }

      // Keep only additionalProperties errors for properties not allowed by the selected branch.
      if (e.keyword === KEYWORDS.additionalProperties) {
        const prop = extractAdditionalPropertyName(e.message);
        // Same idea: prune branch-noise only at the union object itself.
        if (e.instancePath === ctx.path && prop && ctx.selectedBranchProps.has(prop)) return false;
      }
    }
    return true;
  });

  // 2) Marker visibility (selection missing/unknown): keep the parent oneOf marker and drop descendants
  // that would hide it in the tree (getErrorsForTreeRow).
  const keepParentPaths = new Set<string>();
  const dropParentPaths = new Set<string>();
  for (const oneOfError of oneOfErrors) {
    const ctx = contextByPath.get(oneOfError.instancePath);
    if (!ctx) continue;
    if (ctx.selectionKind === 'missing_or_unknown') {
      keepParentPaths.add(oneOfError.instancePath);
    } else {
      dropParentPaths.add(oneOfError.instancePath);
    }
  }

  return branchRestricted.filter((e) => {
    if (keepParentPaths.size > 0 && [...keepParentPaths].some((p) => isStrictDescendantPath(p, e.instancePath))) {
      return false;
    }
    return !(e.keyword === KEYWORDS.oneOf && dropParentPaths.has(e.instancePath));
  });
}

// Run the full cfworker error normalization pipeline (adapt -> prune -> enrich -> policy).
function normalizeCfworkerValidationErrors(
  outputUnits: OutputUnit[],
  schema: SchemaLike,
  data: unknown,
): ValidationError[] {
  // 1) Adapt: OutputUnit[] -> ValidationError[] (adds instancePath, parentSchema, data)
  const adapted = mapLibraryErrorsToValidationErrors(outputUnits, schema, data);

  // 2) Prune: drop cfworker library-level noise that doesn't help the config tree
  const pruned = pruneCfworkerLibraryNoise(adapted);

  // 3) Normalize `items:false` behavior (tuple vs disallow-any)
  const itemsFalseNormalized = normalizeItemsFalseErrors(pruned, schema, data);

  // 4) Normalize `unevaluatedItems:false` behavior: keep array-level marker, drop leaf false-schema noise
  const unevaluatedItemsNormalized = normalizeUnevaluatedItemsFalseErrors(itemsFalseNormalized, schema, data);

  // 5) Enrich: reconstruct missingProperty and leaf paths for required/dependentRequired
  const enriched = enrichMissingPropertyErrors(unevaluatedItemsNormalized);

  // 6) Drop errors produced by evaluating object-only constraints on `null` when schema allows it.
  const nullAligned = dropErrorsForAllowedNullValues(enriched, schema, data);

  // 7) Enrich array-level `contains` to element-level errors for better tree highlighting.
  const containsEnriched = enrichContainsErrors(nullAligned, schema, data);

  // 8) Normalize discriminator-based oneOf behavior (cfworker emits non-selected-branch noise)
  return normalizeDiscriminatorOneOfErrors(containsEnriched);
}

// Validate data with cfworker and return normalized (AJV-like) errors, or null when valid.
export const validateWithCfWorker = (schema: SchemaLike, data: unknown): ValidationError[] | null => {
  if (schema === true) return null;

  if (schema === false) {
    return [createValidationError('', undefined, data, KEYWORDS.falseSchema, MESSAGE_FALSE_SCHEMA)];
  }

  const brokenRef = findFirstBrokenLocalRef(schema);
  if (brokenRef) {
    const rootSchema: Schema | undefined = isSchema(schema) ? schema : undefined;
    return [createValidationError('/', rootSchema, data, '$ref', `can't resolve reference ${brokenRef} from id #`)];
  }

  const unsupported = findFirstUnsupportedKeyword(schema);
  if (unsupported) {
    const rootSchema: Schema | undefined = isSchema(schema) ? schema : undefined;
    return [createValidationError('/', rootSchema, data, '$ref', `strict mode: unknown keyword: "${unsupported}"`)];
  }

  let libraryResult: { valid: boolean; errors: OutputUnit[] | undefined };
  try {
    libraryResult = runValidator(schema, data);
  } catch (e) {
    const rootSchema: Schema | undefined = isSchema(schema) ? schema : undefined;
    const message = e instanceof Error ? e.message : MESSAGE_PATTERN_FALLBACK;
    return [createValidationError('', rootSchema, data, KEYWORDS.pattern, message)];
  }

  const { valid, errors } = libraryResult;
  if (valid || !errors || errors.length === 0) {
    const containsErrors = collectContainsConstraintErrors(schema, data);
    if (containsErrors.length === 0) return null;
    return normalizeDiscriminatorOneOfErrors(enrichContainsErrors(containsErrors, schema, data));
  }

  return normalizeCfworkerValidationErrors(errors, schema, data);
};

// Run cfworker validation and return raw OutputUnit[] (no normalization).
export const validateWithCfWorkerLibrary = (schema: SchemaLike, data: unknown): OutputUnit[] | null => {
  if (schema === true) return null;
  if (schema === false) return null;

  try {
    const { valid, errors } = runValidator(schema, data);
    if (valid || !errors || errors.length === 0) return null;
    return errors;
  } catch {
    return null;
  }
};

// =============================================================================
// Generation helpers
// =============================================================================

// Get object default from schema.default or fall back to `{}`.
function getObjectDefault(schema: Schema): Record<string, unknown> {
  return schema.default && typeof schema.default === 'object'
    ? deepClone(schema.default as Record<string, unknown>)
    : {};
}

// Return true if schema is an object schema (type: object + properties).
function isObjectSchema(s: Schema): boolean {
  return s.type === 'object' && s.properties != null && typeof s.properties === 'object';
}

// Return true if schema is an array schema (type: array + schema `items`).
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

// Read the `static` sub-schema from a oneOf branch (ADCM-specific helper).
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
    const generated = generateFromSchemaWithCfWorker(staticSchema);
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

  const base = schema.default !== undefined ? (deepClone(schema.default) as T) : undefined;
  const selected = selectOneOfBranchByDefault(oneOf);
  const branch = generateFromSchemaWithCfWorker<T>(selected);

  if (branch && typeof branch === 'object' && base && typeof base === 'object') {
    return { ...(base as Record<string, unknown>), ...(branch as Record<string, unknown>) } as T;
  }
  return branch ?? base;
}

/** Object with oneOf (incl. discriminator): select branch by const/default, fill static and defaults. */
function generateFromObjectWithOneOf<T>(schema: Schema): T {
  const result: Record<string, unknown> =
    schema.default && typeof schema.default === 'object' ? deepClone(schema.default as Record<string, unknown>) : {};

  const oneOf = schema.oneOf!;
  const selectedByConst = selectOneOfBranchByConst(oneOf, result);
  const selected = selectedByConst ?? selectOneOfBranchByDefault(oneOf) ?? oneOf[0];

  const branchValue = generateFromSchemaWithCfWorker<T>(selected);
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

    const value = generateFromSchemaWithCfWorker(propSchema);

    if (value && typeof value === 'object' && Array.isArray(propSchema.oneOf)) {
      const valueObj = value as Record<string, unknown>;
      if (valueObj[PROP_STATIC] === undefined) {
        const branchWithStatic = propSchema.oneOf.find((o) => isSchema(o) && o.properties?.[PROP_STATIC] != null);
        const staticSchema = branchWithStatic && getStaticSubSchemaFromBranch(branchWithStatic);
        if (staticSchema?.default !== undefined) {
          valueObj[PROP_STATIC] = deepClone(staticSchema.default);
        }
      }
    }

    if (value !== null && value !== undefined) result[key] = value;
  }

  return result as T;
}

function generateFromArray<T>(schema: Schema): T | undefined {
  if (!isSchema(schema.items)) return undefined;
  const item = generateFromSchemaWithCfWorker(schema.items);

  return (item != null ? [item] : []) as unknown as T;
}

export const generateFromSchemaWithCfWorker = <T>(schema: SchemaLike): T | undefined => {
  if (!isSchema(schema)) return undefined;

  if (schema.default === null) return null as T;

  // oneOf without type: 'object' e.g. type variants or null
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

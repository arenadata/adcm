import type { ConfigurationAttributes, FieldAttributes, SchemaDefinition } from '@models/adcm';
import type { JSONValue, JSONObject } from '@models/json';
import type { ConfigurationNodePath } from '../ConfigurationEditor.types';
import { discriminatorFieldName, rootNodeKey } from './ConfigurationTree.constants';
import type { FieldAttributesSyncPayload } from './ConfigurationTree.types';
import { isObject } from '@utils/objectUtils';

// Drop exact keys listed in removePaths and then apply fieldAttributes per added path.
export const syncFieldAttributes = (
  base: ConfigurationAttributes,
  payload: FieldAttributesSyncPayload,
): ConfigurationAttributes => {
  const next: ConfigurationAttributes = { ...base };

  for (const path of payload.removePaths) {
    delete next[path];
  }

  for (const { path, fieldAttributes } of payload.addPaths) {
    next[path] = fieldAttributes;
  }

  return next;
};

// Convert node path segments to attribute key format used across the editor.
export const buildMetaKey = (path: ConfigurationNodePath) => `${rootNodeKey}${path.join('/')}`;

type MetaDefaults = { isActive?: boolean; isSynchronized?: boolean };
const mergeDefaults = (base: MetaDefaults | undefined, next: MetaDefaults): MetaDefaults => ({
  ...(base ?? {}),
  ...next,
});

const findOneOfByDiscriminator = (
  oneOf: SchemaDefinition['oneOf'],
  disc: string | undefined,
): SchemaDefinition | undefined => {
  if (disc === undefined) return undefined;
  for (const s of oneOf ?? []) {
    if ((s?.properties?.[discriminatorFieldName]?.const as string | undefined) === disc) return s;
  }
  return undefined;
};

export const collectMetaAttributesForSchema = (
  schema: SchemaDefinition | undefined,
  pathPrefix: ConfigurationNodePath,
  value: JSONValue,
  out: Map<string, MetaDefaults>,
) => {
  if (!schema) return;

  // If we hit a nested selectable object, descend into the selected oneOf branch based on runtime value.
  if (schema.oneOf && schema.discriminator && isObject(value)) {
    const v = value as JSONObject;
    const disc = v[discriminatorFieldName] as string | undefined;
    const branch = findOneOfByDiscriminator(schema.oneOf, disc);
    collectMetaAttributesForSchema(branch, pathPrefix, v, out);
    return;
  }

  // Only object properties can contain meta-driven attributes.
  const props = schema.properties;
  if (!props) return;

  for (const propName of Object.keys(props)) {
    const sub = props[propName];
    if (!sub) continue;

    const nextPath = [...pathPrefix, propName];
    const key = buildMetaKey(nextPath);

    // Activation/synchronization are stored in attributes map under the field path key.
    const activationMeta = sub.adcmMeta?.activation;
    if (activationMeta) {
      out.set(key, mergeDefaults(out.get(key), { isActive: activationMeta.default ?? true }));
    }
    const synchronizationMeta = sub.adcmMeta?.synchronization;
    if (synchronizationMeta) {
      out.set(key, mergeDefaults(out.get(key), { isSynchronized: synchronizationMeta.default ?? true }));
    }

    const childValue = isObject(value) ? ((value as JSONObject)[propName] as JSONValue) : null;
    collectMetaAttributesForSchema(sub, nextPath, childValue, out);
  }
};

export const buildOneOfMetaAttributesSyncPayload = (
  fieldSchema: SchemaDefinition,
  currentValue: JSONValue,
  nextValue: JSONValue,
  pathPrefix: ConfigurationNodePath,
): FieldAttributesSyncPayload => {
  const prevSelection = isObject(currentValue)
    ? ((currentValue as JSONObject)[discriminatorFieldName] as string | undefined)
    : undefined;
  const nextSelection = isObject(nextValue)
    ? ((nextValue as JSONObject)[discriminatorFieldName] as string | undefined)
    : undefined;

  // Collect meta keys from the previous branch to delete (activation + synchronization).
  const removePaths: string[] = [];
  if (prevSelection !== undefined && fieldSchema.oneOf) {
    const prevBranch = findOneOfByDiscriminator(fieldSchema.oneOf, prevSelection);
    const prevMap = new Map<string, MetaDefaults>();
    collectMetaAttributesForSchema(prevBranch, pathPrefix, currentValue, prevMap);
    removePaths.push(...prevMap.keys());
  }

  // Collect meta keys for the new branch.
  const addPathsMap = new Map<string, MetaDefaults>();
  if (nextSelection !== undefined && fieldSchema.oneOf) {
    const nextBranch = findOneOfByDiscriminator(fieldSchema.oneOf, nextSelection);
    collectMetaAttributesForSchema(nextBranch, pathPrefix, nextValue, addPathsMap);
  }

  const addPaths: FieldAttributesSyncPayload['addPaths'] = Array.from(addPathsMap, ([path, defaults]) => ({
    path,
    fieldAttributes: defaults as FieldAttributes,
  }));

  return { removePaths, addPaths };
};

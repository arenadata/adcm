import type { ConfigurationData } from '@models/adcm';
import type { JSONValue } from '@models/json';
import { isObject } from '@utils/objectUtils';

export const SELECTION_KEY = '_selection';

const isJSONObject = (value: unknown): value is ConfigurationData => {
  return isObject(value) && !Array.isArray(value);
};

export const isSelectableObject = (value: unknown): value is ConfigurationData => {
  if (!isJSONObject(value)) {
    return false;
  }
  return SELECTION_KEY in value;
};

export const getSelectionFromDraft = (draftValue: unknown): string | undefined => {
  if (isSelectableObject(draftValue)) {
    const selection = draftValue[SELECTION_KEY];
    return typeof selection === 'string' ? selection : undefined;
  }
  return undefined;
};

const getDraftValueAsObject = (
  draftData: ConfigurationData | undefined,
  key: string,
): ConfigurationData | undefined => {
  const draftValue = draftData?.[key];
  return isJSONObject(draftValue) ? draftValue : undefined;
};

const getDraftValueAsSelectable = (
  draftData: ConfigurationData | undefined,
  key: string,
): ConfigurationData | undefined => {
  const draftValue = draftData?.[key];
  return isSelectableObject(draftValue) ? draftValue : undefined;
};

const checkSelectionChanged = (previousSelection: string | undefined, newSelection: string): boolean => {
  return previousSelection !== undefined && previousSelection !== newSelection;
};

const checkHasOwnProperty = (obj: ConfigurationData, key: string): boolean => {
  return Object.prototype.hasOwnProperty.call(obj, key);
};

function mergeWithRawData(
  rawData: ConfigurationData,
  newData: ConfigurationData,
  previousDraftData?: ConfigurationData,
): ConfigurationData {
  const result: ConfigurationData = { ...newData };

  for (const key in newData) {
    if (!checkHasOwnProperty(newData, key)) continue;

    const newValue = newData[key];
    const rawValue = rawData[key];

    // Selectable objects: merge from raw (preserves edited variants)
    if (isJSONObject(newValue) && isSelectableObject(newValue)) {
      if (isJSONObject(rawValue)) {
        const previousDraftSelectable = getDraftValueAsSelectable(previousDraftData, key);
        const previousSelection = previousDraftSelectable ? getSelectionFromDraft(previousDraftSelectable) : undefined;
        result[key] = processSelectableFieldForDraft(newValue, rawValue, previousSelection);
      } else {
        result[key] = newValue;
      }
      continue;
    }

    // Nested objects: recurse to handle nested selectable objects
    if (isJSONObject(newValue) && isJSONObject(rawValue)) {
      const previousDraftObject = getDraftValueAsObject(previousDraftData, key);
      result[key] = mergeWithRawData(rawValue, newValue, previousDraftObject);
      continue;
    }

    // Primitives and arrays: use newData (raw only stores selectable fields)
    result[key] = newValue;
  }

  return result;
}

const mergeVariantValue = (
  rawVariantValue: unknown,
  newVariantValue: unknown,
  isSelectionChanged: boolean,
): JSONValue => {
  // Handle undefined cases
  if (rawVariantValue === undefined) return newVariantValue as JSONValue;
  if (newVariantValue === undefined) return rawVariantValue as JSONValue;

  // Both are objects: merge with priority based on context
  if (isJSONObject(newVariantValue) && isJSONObject(rawVariantValue)) {
    // When switching: raw has priority (preserve edited values)
    // When editing: new has priority (user is editing)
    const baseValue = isSelectionChanged ? rawVariantValue : newVariantValue;
    const overrideValue = isSelectionChanged ? newVariantValue : rawVariantValue;
    const result: ConfigurationData = { ...baseValue };

    // Merge override into base, but base values are not overwritten
    for (const key in overrideValue) {
      if (!checkHasOwnProperty(overrideValue, key)) continue;

      const baseVal = baseValue[key];
      const overrideVal = overrideValue[key];

      // If base already has the key, it wins. For nested objects we still need to merge
      // selectable subobjects. `mergeVariantValue` signature is (raw, new, isSelectionChanged).
      if (baseVal !== undefined) {
        const shouldRecurse = isJSONObject(baseVal) && isJSONObject(overrideVal);
        if (!shouldRecurse) {
          result[key] = baseVal;
          continue;
        }

        const rawChild = (isSelectionChanged ? baseVal : overrideVal) as ConfigurationData;
        const newChild = (isSelectionChanged ? overrideVal : baseVal) as ConfigurationData;
        result[key] = mergeVariantValue(rawChild, newChild, isSelectionChanged);
        continue;
      }

      // If base doesn't have the key:
      // - switching variants: bring keys from the new branch
      // - editing the same variant: don't resurrect deleted keys from raw
      if (isSelectionChanged) {
        result[key] = overrideVal;
      }
    }

    // When editing (not switching), preserve fields from base that are not in override
    if (!isSelectionChanged) {
      for (const key in baseValue) {
        if (!checkHasOwnProperty(baseValue, key) || key in result) continue;
        result[key] = baseValue[key];
      }
    }

    return result;
  }

  // Primitives: base value wins
  return isSelectionChanged ? (rawVariantValue as JSONValue) : (newVariantValue as JSONValue);
};

const processSelectableFieldForDraft = (
  newValueObj: ConfigurationData,
  rawValueObj: ConfigurationData,
  previousSelection?: string,
): ConfigurationData => {
  const newSelectionValue = newValueObj[SELECTION_KEY];
  if (typeof newSelectionValue !== 'string') {
    return { [SELECTION_KEY]: newSelectionValue } as ConfigurationData;
  }

  const newSelection = newSelectionValue;
  const isSelectionChanged = checkSelectionChanged(previousSelection, newSelection);
  const newVariantValue = newValueObj[newSelection];
  const rawVariantValue = rawValueObj[newSelection];
  const mergedVariantValue = mergeVariantValue(rawVariantValue, newVariantValue, isSelectionChanged);

  return {
    [SELECTION_KEY]: newSelection,
    ...(mergedVariantValue !== undefined && { [newSelection]: mergedVariantValue }),
  };
};

function storeRawData(
  rawData: ConfigurationData,
  newData: ConfigurationData,
  currentDraftData?: ConfigurationData,
  persistPlainValues = false,
): ConfigurationData {
  const result: ConfigurationData = {};

  for (const key in newData) {
    if (!checkHasOwnProperty(newData, key)) continue;

    const newValue = newData[key];
    const rawValue = rawData[key];

    // Only store selectable objects in raw data
    if (isJSONObject(newValue) && isSelectableObject(newValue)) {
      const currentDraftSelectable = getDraftValueAsSelectable(currentDraftData, key);
      const rawSelectableObj = isJSONObject(rawValue) ? rawValue : {};
      result[key] = processSelectableFieldForRaw(newValue, rawSelectableObj, currentDraftSelectable);
      continue;
    }

    // For nested objects (non-selectable), recurse to handle nested selectable objects
    if (isJSONObject(newValue)) {
      const currentDraftObject = getDraftValueAsObject(currentDraftData, key);
      const rawObjectValue = isJSONObject(rawValue) ? rawValue : {};
      result[key] = storeRawData(rawObjectValue, newValue, currentDraftObject, persistPlainValues);
      continue;
    }

    // Don't store non-selectable primitives/arrays in raw at top level.
    // But inside selectable variants (persistPlainValues=true), persist them as well.
    if (persistPlainValues) {
      result[key] = newValue;
    } else if (rawValue !== undefined) {
      // Preserve only those primitives that already exist in raw.
      result[key] = newValue;
    }
  }

  return result;
}

const updateVariantInRaw = (
  rawSelectable: ConfigurationData,
  variantKey: string,
  newVariantValue: unknown,
  existingRawVariant: unknown,
  isSelectionChanged: boolean,
  currentDraftVariantData?: ConfigurationData,
): void => {
  if (newVariantValue === undefined) return;

  if (existingRawVariant === undefined) {
    rawSelectable[variantKey] = newVariantValue as JSONValue;
    return;
  }

  if (isJSONObject(newVariantValue) && isJSONObject(existingRawVariant)) {
    rawSelectable[variantKey] = storeRawData(existingRawVariant, newVariantValue, currentDraftVariantData, true);
    return;
  }

  // For primitives: update if editing, preserve if switching
  if (!isSelectionChanged) {
    rawSelectable[variantKey] = newVariantValue as JSONValue;
  }
};

const processSelectableFieldForRaw = (
  newValueObj: ConfigurationData,
  rawValueObj: ConfigurationData,
  currentDraftSelectableData: ConfigurationData | undefined,
): ConfigurationData => {
  const rawSelectable: ConfigurationData = { ...rawValueObj };
  delete rawSelectable[SELECTION_KEY];

  const newSelectionValue = newValueObj[SELECTION_KEY];
  if (typeof newSelectionValue !== 'string') {
    return rawSelectable;
  }

  const newSelection = newSelectionValue;
  const previousSelection = getSelectionFromDraft(currentDraftSelectableData);
  const isSelectionChanged = checkSelectionChanged(previousSelection, newSelection);

  const newVariantValue = newValueObj[newSelection];
  const existingRawVariant = rawSelectable[newSelection];
  const currentDraftVariantData = getDraftValueAsObject(currentDraftSelectableData, newSelection);

  updateVariantInRaw(
    rawSelectable,
    newSelection,
    newVariantValue,
    existingRawVariant,
    isSelectionChanged,
    currentDraftVariantData,
  );

  return rawSelectable;
};

export { mergeWithRawData, storeRawData };

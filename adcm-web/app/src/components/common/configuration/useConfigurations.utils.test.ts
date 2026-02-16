import {
  isSelectableObject,
  getSelectionFromDraft,
  SELECTION_KEY,
  mergeWithRawData,
  storeRawData,
} from './useConfigurations.utils';
import type { ConfigurationData } from '@models/adcm';
import type { JSONValue } from '@models/json';

const getNestedValue = (obj: ConfigurationData, path: string[]): ConfigurationData | undefined => {
  let current: JSONValue | undefined = obj;
  for (const key of path) {
    if (current === null || current === undefined || typeof current !== 'object' || Array.isArray(current)) {
      return undefined;
    }
    if (!(key in current)) {
      return undefined;
    }
    current = current[key];
  }
  if (current === null || current === undefined || typeof current !== 'object' || Array.isArray(current)) {
    return undefined;
  }
  return current;
};

describe('isSelectableObject', () => {
  test('returns true for object with _selection key', () => {
    expect(isSelectableObject({ [SELECTION_KEY]: 'a' })).toBe(true);
  });

  test('returns false for object without _selection key', () => {
    expect(isSelectableObject({ field: 'value' })).toBe(false);
  });

  test('returns false for primitive values', () => {
    expect(isSelectableObject('string')).toBe(false);
    expect(isSelectableObject(123)).toBe(false);
    expect(isSelectableObject(null)).toBe(false);
  });

  test('returns false for arrays', () => {
    expect(isSelectableObject([1, 2, 3])).toBe(false);
  });
});

describe('getSelectionFromDraft', () => {
  test('returns selection string for selectable object', () => {
    expect(getSelectionFromDraft({ [SELECTION_KEY]: 'a' })).toBe('a');
  });

  test('returns undefined for non-string selection', () => {
    expect(getSelectionFromDraft({ [SELECTION_KEY]: null })).toBeUndefined();
    expect(getSelectionFromDraft({ [SELECTION_KEY]: 123 })).toBeUndefined();
  });

  test('returns undefined for non-selectable object', () => {
    expect(getSelectionFromDraft({ field: 'value' })).toBeUndefined();
  });

  test('returns undefined for primitive values', () => {
    expect(getSelectionFromDraft('string')).toBeUndefined();
    expect(getSelectionFromDraft(null)).toBeUndefined();
  });
});

describe('mergeWithRawData', () => {
  test('merges selectable field with raw data when switching variants', () => {
    const rawData: ConfigurationData = {
      selectable: {
        a: { field: 'edited' },
        b: { field: 'default' },
      },
    };
    const newData: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'b',
        b: { field: 'default' },
      },
    };
    const previousDraft: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: { field: 'edited' },
      },
    };

    const result = mergeWithRawData(rawData, newData, previousDraft);

    expect(result.selectable).toEqual({
      [SELECTION_KEY]: 'b',
      b: { field: 'default' },
    });
  });

  test('merges selectable field with raw data when editing same variant', () => {
    const rawData: ConfigurationData = {
      selectable: {
        a: { field: 'old' },
      },
    };
    const newData: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: { field: 'new' },
      },
    };
    const previousDraft: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: { field: 'old' },
      },
    };

    const result = mergeWithRawData(rawData, newData, previousDraft);

    expect(result.selectable).toEqual({
      [SELECTION_KEY]: 'a',
      a: { field: 'new' },
    });
  });

  test('uses new value when raw data is empty', () => {
    const rawData: ConfigurationData = {};
    const newData: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: { field: 'value' },
      },
    };

    const result = mergeWithRawData(rawData, newData);

    expect(result.selectable).toEqual({
      [SELECTION_KEY]: 'a',
      a: { field: 'value' },
    });
  });

  test('preserves non-selectable primitives from newData', () => {
    const rawData: ConfigurationData = {
      primitive: 'old',
    };
    const newData: ConfigurationData = {
      primitive: 'new',
    };

    const result = mergeWithRawData(rawData, newData);

    expect(result.primitive).toBe('new');
  });

  test('recursively merges nested objects', () => {
    const rawData: ConfigurationData = {
      nested: {
        selectable: {
          a: { field: 'edited' },
        },
      },
    };
    const newData: ConfigurationData = {
      nested: {
        selectable: {
          [SELECTION_KEY]: 'a',
          a: { field: 'default' },
        },
      },
    };
    const previousDraft: ConfigurationData = {
      nested: {
        selectable: {
          [SELECTION_KEY]: 'b',
          b: {},
        },
      },
    };

    const result = mergeWithRawData(rawData, newData, previousDraft);
    const nestedSelectable = getNestedValue(result, ['nested', 'selectable']);

    expect(nestedSelectable).toEqual({
      [SELECTION_KEY]: 'a',
      a: { field: 'edited' },
    });
  });
});

describe('storeRawData', () => {
  test('stores selectable field variants in raw data', () => {
    const rawData: ConfigurationData = {};
    const newData: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: { field: 'value' },
      },
    };

    const result = storeRawData(rawData, newData);

    expect(result.selectable).toEqual({
      a: { field: 'value' },
    });
    const selectable = result.selectable as ConfigurationData;
    expect(selectable[SELECTION_KEY]).toBeUndefined();
  });

  test('preserves all variants when switching selection', () => {
    const rawData: ConfigurationData = {
      selectable: {
        a: { field: 'edited' },
      },
    };
    const newData: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'b',
        b: { field: 'default' },
      },
    };
    const currentDraft: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: { field: 'edited' },
      },
    };

    const result = storeRawData(rawData, newData, currentDraft);

    expect(result.selectable).toEqual({
      a: { field: 'edited' },
      b: { field: 'default' },
    });
  });

  test('updates variant when editing same selection', () => {
    const rawData: ConfigurationData = {
      selectable: {
        a: { field: 'old' },
      },
    };
    const newData: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: { field: 'new' },
      },
    };
    const currentDraft: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: { field: 'old' },
      },
    };

    const result = storeRawData(rawData, newData, currentDraft);

    expect(result.selectable).toEqual({
      a: { field: 'new' },
    });
  });

  test('does not store non-selectable primitives at top level', () => {
    const rawData: ConfigurationData = {};
    const newData: ConfigurationData = {
      primitive: 'value',
    };

    const result = storeRawData(rawData, newData);

    expect(result.primitive).toBeUndefined();
  });

  test('updates non-selectable primitives inside variants when editing', () => {
    const rawData: ConfigurationData = {
      selectable: {
        a: { primitive: 'old' },
      },
    };
    const newData: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: { primitive: 'new' },
      },
    };
    const currentDraft: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: { primitive: 'old' },
      },
    };

    const result = storeRawData(rawData, newData, currentDraft);
    const selectable = result.selectable as ConfigurationData;
    const variantA = selectable?.a as ConfigurationData;

    expect(variantA).toEqual({ primitive: 'new' });
  });

  test('recursively stores nested selectable objects', () => {
    const rawData: ConfigurationData = {};
    const newData: ConfigurationData = {
      nested: {
        selectable: {
          [SELECTION_KEY]: 'a',
          a: { field: 'value' },
        },
      },
    };

    const result = storeRawData(rawData, newData);
    const nestedSelectable = getNestedValue(result, ['nested', 'selectable']);

    expect(nestedSelectable).toEqual({
      a: { field: 'value' },
    });
    expect(nestedSelectable?.[SELECTION_KEY]).toBeUndefined();
  });

  test('merges nested objects preserving selectable fields', () => {
    const rawData: ConfigurationData = {
      nested: {
        selectable: {
          a: { field: 'edited' },
        },
      },
    };
    const newData: ConfigurationData = {
      nested: {
        selectable: {
          [SELECTION_KEY]: 'a',
          a: { field: 'default' },
        },
      },
    };
    const currentDraft: ConfigurationData = {
      nested: {
        selectable: {
          [SELECTION_KEY]: 'a',
          a: { field: 'edited' },
        },
      },
    };

    const result = storeRawData(rawData, newData, currentDraft);
    const nestedSelectable = getNestedValue(result, ['nested', 'selectable']);

    expect(nestedSelectable).toEqual({
      a: { field: 'default' },
    });
  });
});

describe('mergeVariantValue integration', () => {
  test('preserves raw values when switching variants with nested objects', () => {
    const rawData: ConfigurationData = {
      selectable: {
        a: {
          nested: { field: 'edited' },
        },
      },
    };
    const newData: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'a',
        a: {
          nested: { field: 'default' },
        },
      },
    };
    const previousDraft: ConfigurationData = {
      selectable: {
        [SELECTION_KEY]: 'b',
        b: {},
      },
    };

    const result = mergeWithRawData(rawData, newData, previousDraft);
    const selectable = result.selectable as ConfigurationData;

    expect(selectable).toEqual({
      [SELECTION_KEY]: 'a',
      a: {
        nested: { field: 'edited' },
      },
    });
  });
});

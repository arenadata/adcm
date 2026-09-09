import { filterInlineStringSuggestions, getInlinePrimitiveFieldControlType } from './InlinePrimitiveFieldControl.utils';

describe('filterInlineStringSuggestions', () => {
  const suggestions = ['localhost', 'host1', 'host2'];

  test('returns all suggestions when value is empty', () => {
    expect(filterInlineStringSuggestions(suggestions, '')).toEqual(suggestions);
  });

  test('filters by case-insensitive includes', () => {
    expect(filterInlineStringSuggestions(suggestions, 'HOST')).toEqual(['localhost', 'host1', 'host2']);
    expect(filterInlineStringSuggestions(suggestions, 'local')).toEqual(['localhost']);
  });

  test('returns empty list when custom value does not match', () => {
    expect(filterInlineStringSuggestions(suggestions, 'custom-host')).toEqual([]);
  });
});

describe('getInlinePrimitiveFieldControlType', () => {
  test('keeps suggestion string fields as inline string, not enum', () => {
    expect(
      getInlinePrimitiveFieldControlType({
        type: 'string',
        adcmMeta: {
          stringExtra: {
            suggestions: ['localhost', 'host1', 'host2'],
          },
        },
      }),
    ).toBe('string');
  });
});

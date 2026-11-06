import { isMappingLayersV2Enabled, MAPPING_LAYERS_V2_STORAGE_KEY } from './isMappingLayersV2Enabled';

describe('isMappingLayersV2Enabled', () => {
  test('query 1 wins over storage false', () => {
    expect(isMappingLayersV2Enabled('?mappingLayers=1', { getItem: () => 'false' })).toBe(true);
  });

  test('query 0 wins over storage true', () => {
    expect(isMappingLayersV2Enabled('?mappingLayers=0', { getItem: () => 'true' })).toBe(false);
  });

  test('no query uses storage', () => {
    expect(
      isMappingLayersV2Enabled('', {
        getItem: (key) => (key === MAPPING_LAYERS_V2_STORAGE_KEY ? 'true' : null),
      }),
    ).toBe(true);
  });

  test('default false', () => {
    expect(isMappingLayersV2Enabled('', { getItem: () => null })).toBe(false);
  });
});

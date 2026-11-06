export const MAPPING_LAYERS_V2_STORAGE_KEY = 'adcm/mappingLayersV2';
export const MAPPING_LAYERS_V2_QUERY = 'mappingLayers';

type MappingLayersStorage = Pick<Storage, 'getItem'>;

const readQueryFlag = (search: string): boolean | undefined => {
  const normalized = search.startsWith('?') ? search.slice(1) : search;
  if (!normalized) {
    return undefined;
  }

  const params = new URLSearchParams(normalized);
  const value = params.get(MAPPING_LAYERS_V2_QUERY);
  if (value === '1') {
    return true;
  }
  if (value === '0') {
    return false;
  }

  return undefined;
};

const readStorageFlag = (storage: MappingLayersStorage): boolean | undefined => {
  const value = storage.getItem(MAPPING_LAYERS_V2_STORAGE_KEY);
  if (value === 'true') {
    console.info('modern mapping');
    return true;
  }
  if (value === 'false') {
    console.info('legacy mapping');
    return false;
  }

  return undefined;
};

export const isMappingLayersV2Enabled = (
  search: string = typeof window !== 'undefined' ? window.location.search : '',
  storage: MappingLayersStorage | undefined = typeof localStorage !== 'undefined' ? localStorage : undefined,
): boolean => {
  const fromQuery = readQueryFlag(search);
  if (fromQuery !== undefined) {
    return fromQuery;
  }

  if (storage) {
    const fromStorage = readStorageFlag(storage);
    if (fromStorage !== undefined) {
      return fromStorage;
    }
  }

  return false;
};

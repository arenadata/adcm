import { useCallback, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { isMappingLayersV2Enabled, MAPPING_LAYERS_V2_STORAGE_KEY } from '@utils/mapping/isMappingLayersV2Enabled';

export const useMappingLayersV2 = (): [boolean, (enabled: boolean) => void] => {
  const [searchParams] = useSearchParams();
  const [storageVersion, setStorageVersion] = useState(0);

  const enabled = useMemo(() => {
    const query = searchParams.toString();
    return isMappingLayersV2Enabled(query ? `?${query}` : '', localStorage);
  }, [searchParams, storageVersion]);

  const setEnabled = useCallback((isEnabled: boolean) => {
    localStorage.setItem(MAPPING_LAYERS_V2_STORAGE_KEY, String(isEnabled));
    setStorageVersion((version) => version + 1);
  }, []);

  return [enabled, setEnabled];
};

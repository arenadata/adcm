import { useSearchParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import qs from 'qs';
import type { AdcmClusterHostsFilter } from '@models/adcm';
import { createInitialState } from '@store/adcm/cluster/hosts/hostsTableSlice';

type DataFromUrl = {
  filter: AdcmClusterHostsFilter;
};

export const useGetFilterFromUrl = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [dataFromUrl, setDataFromUrl] = useState<DataFromUrl | null>(null);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);

  useEffect(() => {
    const filterFromUrl: Partial<AdcmClusterHostsFilter> = qs.parse(
      searchParams.toString(),
    ) as Partial<AdcmClusterHostsFilter>;

    if (Object.keys(filterFromUrl).length > 0) {
      setDataFromUrl({
        filter: {
          ...createInitialState().filter,
          ...filterFromUrl,
        },
      });
      setSearchParams({});
    }

    setIsLoaded(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    isLoaded,
    dataFromUrl,
  };
};

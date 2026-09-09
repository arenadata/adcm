import { EMPTY_ARRAY } from '@constants';
import { useStore } from '@hooks';

export type { MaintenanceEntityItem } from '@store/adcm/clusters/clusterMaintenanceModeSlice';

export const useClusterMaintenanceMode = (clusterId: number) => {
  const data = useStore((state) => state.adcm.clusterMaintenanceMode.byClusterId[clusterId]);

  const servicesCount = data?.servicesCount ?? 0;
  const hostsCount = data?.hostsCount ?? 0;

  return {
    services: data?.services ?? EMPTY_ARRAY,
    hosts: data?.hosts ?? EMPTY_ARRAY,
    servicesCount,
    hostsCount,
    hasMaintenanceMode: servicesCount > 0 || hostsCount > 0,
  };
};

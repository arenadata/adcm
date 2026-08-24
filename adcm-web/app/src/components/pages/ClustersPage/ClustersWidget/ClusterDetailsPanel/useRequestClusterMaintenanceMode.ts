import { useEffect } from 'react';
import { useDispatch } from '@hooks';
import { loadClusterMaintenanceMode } from '@store/adcm/clusters/clusterMaintenanceModeSlice';

export const useRequestClusterMaintenanceMode = (clusterId: number) => {
  const dispatch = useDispatch();

  useEffect(() => {
    if (!clusterId) {
      return;
    }

    dispatch(loadClusterMaintenanceMode(clusterId));
  }, [clusterId, dispatch]);
};

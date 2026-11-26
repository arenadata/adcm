import type React from 'react';
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useStore, useLocalStorage, useMappingLayersV2 } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { getMappings, cleanupMappings, getNotAddedServices } from '@store/adcm/cluster/mapping/mappingSlice';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';
import ClusterMappingLegacy from './ClusterMappingLegacy';
import ClusterMappingV2 from './ClusterMappingV2';

const ClusterMappingWrapper: React.FC = () => {
  const accessCheckStatus = useStore(({ adcm }) => adcm.clusterMapping.accessCheckStatus);
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const dispatch = useDispatch();
  const [mappingLayersV2] = useMappingLayersV2();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const [isHostsPreviewMode, saveIsHostsPreviewModeToStorage] = useLocalStorage<boolean>({
    key: 'adcm/clusters_mapping_hostsPreviewMode',
    initData: false,
    isUserDependencies: true,
  });

  useEffect(() => {
    if (!Number.isNaN(clusterId)) {
      dispatch(getMappings({ clusterId }));
      dispatch(getNotAddedServices({ clusterId }));
    }

    return () => {
      dispatch(cleanupMappings());
    };
  }, [clusterId, dispatch]);

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Mapping' },
          { label: isHostsPreviewMode ? 'Hosts view' : 'Components view' },
        ]),
      );
    }
  }, [cluster, isHostsPreviewMode, dispatch]);

  const MappingBody = mappingLayersV2 ? ClusterMappingV2 : ClusterMappingLegacy;

  return (
    <PermissionsChecker requestState={accessCheckStatus}>
      <MappingBody
        isHostsPreviewMode={isHostsPreviewMode}
        saveIsHostsPreviewModeToStorage={saveIsHostsPreviewModeToStorage}
      />
    </PermissionsChecker>
  );
};

export default ClusterMappingWrapper;

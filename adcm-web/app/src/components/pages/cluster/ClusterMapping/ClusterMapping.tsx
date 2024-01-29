import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useStore } from '@hooks';
import ClusterMappingToolbar from './ClusterMappingToolbar/ClusterMappingToolbar';
import ComponentsMapping from './ComponentsMapping/ComponentsMapping';
import HostsMapping from './HostsMapping/HostsMapping';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import {
  getMappings,
  cleanupMappings,
  getNotAddedServices,
  saveMapping,
} from '@store/adcm/cluster/mapping/mappingSlice';
import { useClusterMapping } from './useClusterMapping';
import s from './ClusterMapping.module.scss';

const ClusterMapping: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const [isHostsPreviewMode, setIsHostsPreviewMode] = useState<boolean>(false);

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
        ]),
      );
    }
  }, [cluster, dispatch]);

  const { mapping, hosts, components, loading, saving } = useStore(({ adcm }) => adcm.clusterMapping);
  const notAddedServicesDictionary = useStore(({ adcm }) => adcm.clusterMapping.relatedData.notAddedServicesDictionary);

  const {
    localMapping,
    mappingFilter,
    servicesMapping,
    hostsMapping,
    mappingValidation,
    isMappingChanged,
    handleMap,
    handleUnmap,
    handleMappingFilterChange,
    handleReset,
  } = useClusterMapping(mapping, hosts, components, notAddedServicesDictionary, loading.state === 'completed');

  const handleSave = () => {
    dispatch(saveMapping({ clusterId, mapping: localMapping }));
  };

  return (
    <div className={s.clusterMapping}>
      <ClusterMappingToolbar
        filter={mappingFilter}
        isHostsPreviewMode={isHostsPreviewMode}
        hasSaveError={saving.hasError}
        isValid={mappingValidation.isAllMappingValid}
        savingState={saving.state}
        isMappingChanged={isMappingChanged}
        onFilterChange={handleMappingFilterChange}
        onHostsPreviewModeChange={setIsHostsPreviewMode}
        onReset={handleReset}
        onSave={handleSave}
      />
      {isHostsPreviewMode ? (
        <HostsMapping
          //
          hostsMapping={hostsMapping}
          mappingFilter={mappingFilter}
          mappingValidation={mappingValidation}
        />
      ) : (
        <ComponentsMapping
          hosts={hosts}
          servicesMapping={servicesMapping}
          mappingValidation={mappingValidation}
          mappingFilter={mappingFilter}
          notAddedServicesDictionary={notAddedServicesDictionary}
          onMap={handleMap}
          onUnmap={handleUnmap}
        />
      )}
    </div>
  );
};

export default ClusterMapping;

import type React from 'react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useStore, usePrevious, useLocalStorage } from '@hooks';
import { Switch } from '@uikit';
import ClusterMappingToolbar from './ClusterMappingToolbar/ClusterMappingToolbar';
import ComponentsMapping from './ComponentsMapping/ComponentsMapping';
import HostsMapping from './HostsMapping/HostsMapping';
import RequiredServicesDialog from './RequiredServicesDialog/RequiredServicesDialog';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import {
  getMappings,
  cleanupMappings,
  getNotAddedServices,
  saveMappingWithUpdate,
  openRequiredServicesDialog,
} from '@store/adcm/cluster/mapping/mappingSlice';
import { useClusterMapping } from './useClusterMapping';
import s from './ClusterMapping.module.scss';
import type { AdcmMappingComponent, HostId } from '@models/adcm';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';
import {
  checkComponentMappingAvailability,
  checkHostMappingAvailability,
  checkHostUnmappingAvailability,
} from './ClusterMapping.utils.ts';

interface ClusterMappingProps {
  isHostsPreviewMode: boolean | null;
  saveIsHostsPreviewModeToStorage: (itemData: boolean) => void;
}

const ClusterMapping: React.FC<ClusterMappingProps> = ({ isHostsPreviewMode, saveIsHostsPreviewModeToStorage }) => {
  const dispatch = useDispatch();
  const { mapping, hosts, components, loading, saving } = useStore(({ adcm }) => adcm.clusterMapping);
  const notAddedServicesDictionary = useStore(({ adcm }) => adcm.clusterMapping.relatedData.notAddedServicesDictionary);

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const [hasSaveError, setHasSaveError] = useState(false);

  const {
    localMapping,
    mappingFilter,
    mappingSortDirection,
    servicesMapping,
    hostsMapping,
    mappingErrors,
    isMappingChanged,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    handleMappingFilterChange,
    handleMappingSortDirectionChange,
    handleReset,
    initiallyMappedHosts,
    initiallyMappedComponents,
  } = useClusterMapping(mapping, hosts, components, notAddedServicesDictionary, loading.state === 'completed');

  const prevLocalMapping = usePrevious(localMapping);

  useEffect(() => {
    if (hasSaveError && localMapping !== prevLocalMapping) {
      setHasSaveError(false);
    }
  }, [prevLocalMapping, localMapping, hasSaveError]);

  const handleSave = async () => {
    try {
      await dispatch(saveMappingWithUpdate({ clusterId, mapping: localMapping })).unwrap();
    } catch {
      setHasSaveError(true);
    }
  };

  const handleInstallServices = (component: AdcmMappingComponent) => {
    dispatch(openRequiredServicesDialog(component));
  };

  const handleHostsPreviewModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    saveIsHostsPreviewModeToStorage(event.target.checked);
  };

  const isValid = Object.keys(mappingErrors).length === 0;

  return (
    <>
      <div className={s.clusterMapping}>
        <ClusterMappingToolbar
          filter={mappingFilter}
          sortDirection={mappingSortDirection}
          hasSaveError={hasSaveError}
          isValid={isValid}
          savingState={saving.state}
          isMappingChanged={isMappingChanged}
          onFilterChange={handleMappingFilterChange}
          onSortDirectionChange={handleMappingSortDirectionChange}
          onReset={handleReset}
          onSave={handleSave}
        />
        <Switch
          className={s.hostsModeSwitch}
          size="small"
          isToggled={isHostsPreviewMode ?? false}
          onChange={handleHostsPreviewModeChange}
          label="Hosts mode"
        />
        {isHostsPreviewMode ? (
          <HostsMapping
            components={components}
            hostsMapping={hostsMapping}
            mappingFilter={mappingFilter}
            mappingErrors={mappingErrors}
            onMap={handleMapComponentsToHost}
            onUnmap={handleUnmap}
            onInstallServices={handleInstallServices}
            checkComponentMappingAvailability={checkComponentMappingAvailability}
            checkHostMappingAvailability={(host, component) => {
              let initMappedHosts: Set<HostId> | undefined;
              if (component?.id) {
                // if check mapping to component - get initMappedHosts by componentId
                initMappedHosts = initiallyMappedHosts[component?.id];
              } else if (initiallyMappedComponents[host.id]?.size) {
                // alter case - we check absolute available of host:
                // we should check case, when host had mapped components but user local remove it
                // in this case we don't full block this host, and we create fake initMappedHosts with this hostId
                initMappedHosts = new Set([host.id]);
              }
              return checkHostMappingAvailability(host, initMappedHosts);
            }}
            checkHostUnmappingAvailability={(host, component) => {
              let initMappedHosts: Set<HostId> | undefined;
              if (component?.id) {
                initMappedHosts = initiallyMappedHosts[component?.id];
              } else if (initiallyMappedComponents[host.id]?.size) {
                initMappedHosts = new Set([host.id]);
              }
              return checkHostUnmappingAvailability(host, initMappedHosts);
            }}
          />
        ) : (
          <ComponentsMapping
            hosts={hosts}
            servicesMapping={servicesMapping}
            mappingErrors={mappingErrors}
            mappingFilter={mappingFilter}
            onMap={handleMapHostsToComponent}
            onUnmap={handleUnmap}
            onInstallServices={handleInstallServices}
            initiallyMappedHosts={initiallyMappedHosts}
          />
        )}

        <RequiredServicesDialog />
      </div>
    </>
  );
};

const ClusterMappingWrapper: React.FC = () => {
  const accessCheckStatus = useStore(({ adcm }) => adcm.clusterMapping.accessCheckStatus);
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const dispatch = useDispatch();

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

  return (
    <PermissionsChecker requestState={accessCheckStatus}>
      <ClusterMapping
        isHostsPreviewMode={isHostsPreviewMode}
        saveIsHostsPreviewModeToStorage={saveIsHostsPreviewModeToStorage}
      />
    </PermissionsChecker>
  );
};

export default ClusterMappingWrapper;

import type React from 'react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useStore, usePrevious } from '@hooks';
import { Switch } from '@uikit';
import ClusterMappingToolbar from './ClusterMappingToolbar/ClusterMappingToolbar';
import ComponentsMapping from './ComponentsMapping/ComponentsMapping';
import HostsMapping from './HostsMapping/HostsMapping';
import RequiredServicesDialog from './RequiredServicesDialog/RequiredServicesDialog';
import { saveMappingWithUpdate, openRequiredServicesDialog } from '@store/adcm/cluster/mapping/mappingSlice';
import { useClusterMapping } from './useClusterMapping';
import s from './ClusterMapping.module.scss';
import type { AdcmMappingComponent, HostId } from '@models/adcm';
import {
  checkComponentMappingAvailability,
  checkHostMappingAvailability,
  checkHostUnmappingAvailability,
} from './ClusterMapping.utils.ts';

interface ClusterMappingLegacyProps {
  isHostsPreviewMode: boolean | null;
  saveIsHostsPreviewModeToStorage: (itemData: boolean) => void;
}

const ClusterMappingLegacy: React.FC<ClusterMappingLegacyProps> = ({
  isHostsPreviewMode,
  saveIsHostsPreviewModeToStorage,
}) => {
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
              initMappedHosts = initiallyMappedHosts[component?.id];
            } else if (initiallyMappedComponents[host.id]?.size) {
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
  );
};

export default ClusterMappingLegacy;

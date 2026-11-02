import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useStore, usePrevious } from '@hooks';
import { Switch } from '@uikit';
import ClusterMappingToolbar from './ClusterMappingToolbar/ClusterMappingToolbar';
import ComponentsMappingV2 from './ComponentsMapping/ComponentsMappingV2';
import HostsMappingV2 from './HostsMapping/HostsMappingV2';
import RequiredServicesDialog from './RequiredServicesDialog/RequiredServicesDialog';
import { saveMappingWithUpdate, openRequiredServicesDialog } from '@store/adcm/cluster/mapping/mappingSlice';
import { useClusterMappingV2 } from './useClusterMappingV2';
import s from './ClusterMapping.module.scss';
import type { AdcmMappingComponent } from '@models/adcm';

interface ClusterMappingV2Props {
  isHostsPreviewMode: boolean | null;
  saveIsHostsPreviewModeToStorage: (itemData: boolean) => void;
}

const ClusterMappingV2: React.FC<ClusterMappingV2Props> = ({ isHostsPreviewMode, saveIsHostsPreviewModeToStorage }) => {
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
    relations,
  } = useClusterMappingV2(
    mapping,
    hosts,
    components,
    notAddedServicesDictionary,
    loading.state === 'completed',
    isHostsPreviewMode ? 'hosts' : 'services',
  );

  const prevLocalMapping = usePrevious(localMapping);

  useEffect(() => {
    if (hasSaveError && localMapping !== prevLocalMapping) {
      setHasSaveError(false);
    }
  }, [prevLocalMapping, localMapping, hasSaveError]);

  const handleSave = useCallback(async () => {
    try {
      await dispatch(saveMappingWithUpdate({ clusterId, mapping: localMapping })).unwrap();
    } catch {
      setHasSaveError(true);
    }
  }, [clusterId, dispatch, localMapping]);

  const handleInstallServices = useCallback(
    (component: AdcmMappingComponent) => {
      dispatch(openRequiredServicesDialog(component));
    },
    [dispatch],
  );

  const handleHostsPreviewModeChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      saveIsHostsPreviewModeToStorage(event.target.checked);
    },
    [saveIsHostsPreviewModeToStorage],
  );

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
      {relations &&
        (isHostsPreviewMode ? (
          <HostsMappingV2
            components={components}
            hostsMapping={hostsMapping}
            mappingFilter={mappingFilter}
            mappingErrors={mappingErrors}
            onMap={handleMapComponentsToHost}
            onUnmap={handleUnmap}
            onInstallServices={handleInstallServices}
            relations={relations}
          />
        ) : (
          <ComponentsMappingV2
            hosts={hosts}
            servicesMapping={servicesMapping}
            mappingErrors={mappingErrors}
            mappingFilter={mappingFilter}
            onMap={handleMapHostsToComponent}
            onUnmap={handleUnmap}
            onInstallServices={handleInstallServices}
            relations={relations}
          />
        ))}

      <RequiredServicesDialog />
    </div>
  );
};

export default ClusterMappingV2;

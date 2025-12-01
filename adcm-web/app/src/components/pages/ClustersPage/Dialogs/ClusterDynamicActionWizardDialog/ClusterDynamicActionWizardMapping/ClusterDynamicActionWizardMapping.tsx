import type React from 'react';
import { useEffect, useMemo, useState } from 'react';
import type { AdcmActionProcessMappingStep } from '@models/adcm/wizard';
import { useDispatch, useLocalStorage, usePrevious, useStore } from '@hooks';
import { getInitiallyMappedHostsDictionary } from '@commonComponents/DynamicActionDialog/DynamicActionSteps/DynamicActionHostMapping/DynamicActionHostMapping.utils';
import { useClusterDynamicActionWizardMapping } from './useClusterDynamicActionWizardMapping';
import { LoadState } from '@models/loadState';
import { getMappings, openRequiredServicesDialog } from '@store/adcm/clusters/clustersWizardSlice';
import type { AdcmMappingComponent } from '@models/adcm';
import s from './ClusterDynamicActionWizardMapping.module.scss';
import ActionWizardMappingToolbar from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMappingToolbar/ActionWizardMappingToolbar';
import HostsMapping from '@pages/cluster/ClusterMapping/HostsMapping/HostsMapping';
import ActionWizardComponentsMapping from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardComponentsMapping/ActionWizardComponentsMapping';
import RequiredServicesDialog from '@pages/cluster/ClusterMapping/RequiredServicesDialog/RequiredServicesDialog';
import { applyMappingDelta } from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMapping.utils';

interface ClusterDynamicActionWizardMappingProps {
  step: AdcmActionProcessMappingStep;
  isReadOnly?: boolean;
}

const ClusterDynamicActionWizardMapping: React.FC<ClusterDynamicActionWizardMappingProps> = ({
  step,
  isReadOnly = false,
}: ClusterDynamicActionWizardMappingProps) => {
  const dispatch = useDispatch();
  const clusterId = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.clusterId);
  const hosts = useStore(({ adcm }) => adcm.clustersWizard.mapping.hosts);
  const components = useStore(({ adcm }) => adcm.clustersWizard.mapping.components);
  const mapping = useStore(({ adcm }) => adcm.clustersWizard.mapping.mapping);
  const loadState = useStore(({ adcm }) => adcm.clustersWizard.mapping.loadState);
  const notAddedServicesDictionary = useStore(({ adcm }) => adcm.clustersWizard.mapping.notAddedServicesDictionary);

  const initiallyMappedHosts = useMemo(() => getInitiallyMappedHostsDictionary(mapping), [mapping]);

  const [isHostsPreviewMode, saveIsHostsPreviewModeToStorage] = useLocalStorage<boolean>({
    key: 'adcm/wizard_mapping_hostsPreviewMode',
    initData: false,
    isUserDependencies: true,
  });
  const [hasSaveError, setHasSaveError] = useState(false);

  const mappingWithDelta = useMemo(
    () => applyMappingDelta(mapping, step.cumulativeDelta),
    [mapping, step.cumulativeDelta],
  );

  const {
    localMapping,
    mappingFilter,
    mappingSortDirection,
    servicesMapping,
    hostsMapping,
    mappingErrors,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    handleMappingFilterChange,
    handleMappingSortDirectionChange,
  } = useClusterDynamicActionWizardMapping(
    mappingWithDelta,
    hosts,
    components,
    notAddedServicesDictionary,
    loadState === LoadState.Loaded,
  );

  const prevLocalMapping = usePrevious(localMapping);

  useEffect(() => {
    if (clusterId && !Number.isNaN(clusterId)) {
      dispatch(getMappings({ clusterId }));
    }
  }, [clusterId, dispatch]);

  useEffect(() => {
    if (hasSaveError && localMapping !== prevLocalMapping) {
      setHasSaveError(false);
    }
  }, [prevLocalMapping, localMapping, hasSaveError]);

  const handleHostsPreviewModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    saveIsHostsPreviewModeToStorage(event.target.checked);
  };

  const handleInstallServices = (component: AdcmMappingComponent) => {
    dispatch(openRequiredServicesDialog(component));
  };

  return (
    <div className={s.wizardMapping}>
      <ActionWizardMappingToolbar
        filter={mappingFilter}
        sortDirection={mappingSortDirection}
        isHostsPreviewMode={isHostsPreviewMode ?? false}
        onHostModeChange={handleHostsPreviewModeChange}
        onFilterChange={handleMappingFilterChange}
        onSortDirectionChange={handleMappingSortDirectionChange}
      />
      {isHostsPreviewMode ? (
        <HostsMapping
          //
          components={components}
          hostsMapping={hostsMapping}
          mappingFilter={mappingFilter}
          mappingErrors={mappingErrors}
          onMap={handleMapComponentsToHost}
          onUnmap={handleUnmap}
          onInstallServices={handleInstallServices}
          isReadOnly={isReadOnly}
        />
      ) : (
        <ActionWizardComponentsMapping
          clusterId={clusterId}
          hosts={hosts}
          rules={step.rules}
          initiallyMappedHosts={initiallyMappedHosts}
          servicesMapping={servicesMapping}
          mappingErrors={mappingErrors}
          mappingFilter={mappingFilter}
          onMap={handleMapHostsToComponent}
          onUnmap={handleUnmap}
          isReadOnly={isReadOnly}
        />
      )}
      <RequiredServicesDialog />
    </div>
  );
};

export default ClusterDynamicActionWizardMapping;

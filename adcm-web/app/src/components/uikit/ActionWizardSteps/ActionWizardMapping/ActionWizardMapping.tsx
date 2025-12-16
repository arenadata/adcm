import type React from 'react';
import { useEffect, useMemo, useState } from 'react';
import type { AdcmActionProcessMappingStep } from '@models/adcm/wizard';
import { useDispatch, useLocalStorage, usePrevious, useStore } from '@hooks';
import { getInitiallyMappedHostsDictionary } from '@commonComponents/DynamicActionDialog/DynamicActionSteps/DynamicActionHostMapping/DynamicActionHostMapping.utils';
import { LoadState } from '@models/loadState';
import type { AdcmMappingComponent } from '@models/adcm';
import ActionWizardMappingToolbar from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMappingToolbar/ActionWizardMappingToolbar';
import HostsMapping from '@pages/cluster/ClusterMapping/HostsMapping/HostsMapping';
import ActionWizardComponentsMapping from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardComponentsMapping/ActionWizardComponentsMapping';
import RequiredServicesDialog from '@pages/cluster/ClusterMapping/RequiredServicesDialog/RequiredServicesDialog';
import { applyMappingDelta } from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMapping.utils';
import { useActionWizardMapping } from '@uikit/ActionWizardSteps/ActionWizardMapping/useActionWizardMapping';
import s from './ActionWizardMapping.module.scss';
import { getMappings, openRequiredServicesDialog } from '@store/adcm/clusters/clustersWizardMappingSlice';

interface ActionWizardMappingProps {
  clusterId: number;
  step: AdcmActionProcessMappingStep;
  onSetIsValid: (isValid: boolean) => void;
  onClose: () => void;
  isReadOnly?: boolean;
}

const ActionWizardMapping: React.FC<ActionWizardMappingProps> = ({
  clusterId,
  step,
  onSetIsValid,
  onClose,
  isReadOnly = false,
}: ActionWizardMappingProps) => {
  const dispatch = useDispatch();
  const hosts = useStore(({ adcm }) => adcm.clustersWizardMapping.mapping.hosts);
  const components = useStore(({ adcm }) => adcm.clustersWizardMapping.mapping.components);
  const mapping = useStore(({ adcm }) => adcm.clustersWizardMapping.mapping.mapping);
  const loadState = useStore(({ adcm }) => adcm.clustersWizardMapping.mapping.loadState);
  const notAddedServicesDictionary = useStore(
    ({ adcm }) => adcm.clustersWizardMapping.mapping.notAddedServicesDictionary,
  );

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

  const initiallyMappedHosts = useMemo(() => getInitiallyMappedHostsDictionary(mappingWithDelta), [mappingWithDelta]);

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
  } = useActionWizardMapping(
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
  }, [clusterId, step.state, dispatch]);

  useEffect(() => {
    if (hasSaveError && localMapping !== prevLocalMapping) {
      setHasSaveError(false);
    }
  }, [prevLocalMapping, localMapping, hasSaveError]);

  useEffect(() => {
    const hasAnyErrors = servicesMapping.some((item) => item.hasErrors);
    onSetIsValid(!hasAnyErrors);
  }, [servicesMapping]);

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
          onClose={onClose}
          isReadOnly={isReadOnly}
        />
      )}
      <RequiredServicesDialog />
    </div>
  );
};

export default ActionWizardMapping;

import type React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { AdcmActionProcessMappingStep } from '@models/adcm/wizard';
import { useDispatch, useLocalStorage, usePrevious, useStore } from '@hooks';
import { LoadState } from '@models/loadState';
import type { AdcmMappingComponent } from '@models/adcm';
import ActionWizardMappingToolbar from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMappingToolbar/ActionWizardMappingToolbar';
import ActionWizardComponentsMappingV2 from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardComponentsMapping/ActionWizardComponentsMappingV2';
import RequiredServicesDialog from '@pages/cluster/ClusterMapping/RequiredServicesDialog/RequiredServicesDialog';
import HostsMappingV2 from '@pages/cluster/ClusterMapping/HostsMapping/HostsMappingV2';
import { applyMappingDelta } from '@utils/mapping/applyMappingDelta';
import { useWizardMapping } from './useWizardMapping';
import s from './ActionWizardMapping.module.scss';
import { getMappings, openRequiredServicesDialog } from '@store/adcm/clusters/clustersWizardMappingSlice';

interface ActionWizardMappingV2Props {
  clusterId: number;
  step: AdcmActionProcessMappingStep;
  onSetIsValid: (isValid: boolean) => void;
  onClose: () => void;
  isReadOnly?: boolean;
}

const ActionWizardMappingV2: React.FC<ActionWizardMappingV2Props> = ({
  clusterId,
  step,
  onSetIsValid,
  onClose,
  isReadOnly = false,
}) => {
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

  const baselineMapping = useMemo(
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
    relations,
  } = useWizardMapping(
    baselineMapping,
    hosts,
    components,
    notAddedServicesDictionary,
    loadState === LoadState.Loaded,
    step,
    isHostsPreviewMode ? 'hosts' : 'services',
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
  }, [servicesMapping, onSetIsValid]);

  const handleHostsPreviewModeChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      saveIsHostsPreviewModeToStorage(event.target.checked);
    },
    [saveIsHostsPreviewModeToStorage],
  );

  const handleInstallServices = useCallback(
    (component: AdcmMappingComponent) => {
      dispatch(openRequiredServicesDialog(component));
    },
    [dispatch],
  );

  return (
    <div className={s.wizardMapping}>
      <ActionWizardMappingToolbar
        filter={mappingFilter}
        sortDirection={mappingSortDirection}
        isHostsPreviewMode={isHostsPreviewMode ?? false}
        onHostModeChange={handleHostsPreviewModeChange}
        onFilterChange={handleMappingFilterChange}
        onSortDirectionChange={handleMappingSortDirectionChange}
        forceShowHostsSwitch
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
            isReadOnly={isReadOnly}
            relations={relations}
          />
        ) : (
          <ActionWizardComponentsMappingV2
            clusterId={clusterId}
            hosts={hosts}
            servicesMapping={servicesMapping}
            mappingErrors={mappingErrors}
            mappingFilter={mappingFilter}
            onMap={handleMapHostsToComponent}
            onUnmap={handleUnmap}
            onClose={onClose}
            isReadOnly={isReadOnly}
            relations={relations}
          />
        ))}
      <RequiredServicesDialog />
    </div>
  );
};

export default ActionWizardMappingV2;

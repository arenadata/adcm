import { useEffect, useMemo } from 'react';
import type { AdcmHostShortView, AdcmMapping, AdcmMappingComponent, NotAddedServicesDictionary } from '@models/adcm';
import type { AdcmActionProcessMappingStep } from '@models/adcm/wizard';
import { useDispatch } from '@hooks';
import { useMappingEditor } from '@hooks/useMappingEditor';
import { diffMapping } from '@utils/mapping/diffMapping';
import {
  cleanupClustersWizardMapping,
  setHostComponentMapDelta,
} from '@store/adcm/clusters/clustersWizardMappingSlice';
import { showInfo } from '@store/notificationsSlice.ts';
import type { MappingLayoutKind, MappingViewConfig } from '@utils/mapping/mapping.types';

export const useWizardMapping = (
  baselineMapping: AdcmMapping[],
  hosts: AdcmHostShortView[],
  components: AdcmMappingComponent[],
  notAddedServicesDictionary: NotAddedServicesDictionary,
  isLoaded: boolean,
  step: AdcmActionProcessMappingStep,
  kind: MappingLayoutKind = 'services',
) => {
  const dispatch = useDispatch();

  const viewConfig = useMemo((): MappingViewConfig => {
    return {
      strategy: {
        type: 'actionRules',
        rules: (step.rules ?? []).map((rule) => ({
          service: rule.service,
          component: rule.component,
          operation: rule.operation,
        })),
      },
      kind,
      sort: 'editableFirst',
    };
  }, [step.rules, kind]);

  const editor = useMappingEditor(baselineMapping, hosts, components, notAddedServicesDictionary, isLoaded, viewConfig);

  useEffect(() => {
    dispatch(setHostComponentMapDelta(diffMapping(baselineMapping, editor.localMapping)));
  }, [dispatch, baselineMapping, editor.localMapping]);

  useEffect(() => {
    return () => {
      dispatch(cleanupClustersWizardMapping());
    };
  }, [dispatch]);

  const unmappedHostsId = editor.unmappedHostsId;
  const unmappedHostsIdStringHash = JSON.stringify(unmappedHostsId);

  useEffect(() => {
    if (!unmappedHostsId.length) {
      return;
    }
    dispatch(showInfo({ message: `Unmapped connection at step ${step.displayName}` }));
  }, [unmappedHostsIdStringHash, dispatch, step.displayName, unmappedHostsId.length]);

  const servicesMapping = editor.viewModel?.kind === 'services' ? editor.viewModel.services : editor.servicesMapping;
  const hostsMapping = editor.viewModel?.kind === 'hosts' ? editor.viewModel.hosts : editor.hostsMapping;

  return {
    ...editor,
    servicesMapping,
    hostsMapping,
  };
};

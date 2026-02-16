import type React from 'react';
import { useMemo } from 'react';
import HostsMapping, { type HostsMappingProps } from '@pages/cluster/ClusterMapping/HostsMapping/HostsMapping.tsx';
import type { AdcmActionProcessMappingStepRules } from '@models/adcm/wizard.ts';
import type {
  AdcmHostComponentMapRuleAction,
  AdcmHostShortView,
  AdcmMappingComponent,
  ComponentId,
  HostId,
} from '@models/adcm';
import {
  checkComponentActionsMappingAvailability,
  checkHostActionsMappingAvailability,
  checkHostActionsUnmappingAvailability,
} from '@commonComponents/DynamicActionDialog/DynamicActionSteps/DynamicActionHostMapping/DynamicActionHostMapping.utils.ts';
import type {
  InitiallyMappedComponentsDictionary,
  InitiallyMappedHostsDictionary,
  ServiceMapping,
} from '@pages/cluster/ClusterMapping/ClusterMapping.types.ts';
import { getComponentMapActions } from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMapping.utils.ts';

type ActionWizardHostsMappingProps = Omit<
  HostsMappingProps,
  'checkHostMappingAvailability' | 'checkHostUnmappingAvailability' | 'checkComponentMappingAvailability'
> & {
  rules: AdcmActionProcessMappingStepRules[];
  servicesMapping: ServiceMapping[];
  initiallyMappedHosts: InitiallyMappedHostsDictionary;
  initiallyMappedComponents: InitiallyMappedComponentsDictionary;
};

const ActionWizardHostsMapping: React.FC<ActionWizardHostsMappingProps> = ({
  rules,
  servicesMapping,
  initiallyMappedHosts,
  initiallyMappedComponents,
  ...props
}) => {
  const allowActionsDictionary = useMemo(() => {
    const result: Record<ComponentId, Set<AdcmHostComponentMapRuleAction>> = {};
    for (const { service, componentsMapping } of servicesMapping) {
      for (const { component } of componentsMapping) {
        const allowActions = getComponentMapActions(rules, service, component);
        result[component.id] = allowActions;
      }
    }
    return result;
  }, [rules, servicesMapping]);

  const checkHostMappingAvailability = (host: AdcmHostShortView, component?: AdcmMappingComponent) => {
    const componentId = component?.id;

    const allowActions = componentId ? allowActionsDictionary[componentId] : undefined;
    let initMappedHosts: Set<HostId> | undefined;
    if (componentId) {
      // if check mapping to component - get initMappedHosts by componentId
      initMappedHosts = initiallyMappedHosts[componentId];
    } else if (initiallyMappedComponents[host.id]?.size) {
      // alter case - we check absolute available of host:
      // we should check case, when host had mapped components but user local remove it
      // in this case we don't full block this host, and we create fake initMappedHosts with this hostId
      initMappedHosts = new Set([host.id]);
    }
    // const initMappedHosts = componentId ? initiallyMappedHosts[componentId] : undefined;
    return checkHostActionsMappingAvailability(host, allowActions, initMappedHosts);
  };

  const checkHostUnmappingAvailability = (host: AdcmHostShortView, component?: AdcmMappingComponent) => {
    const componentId = component?.id;

    const allowActions = componentId ? allowActionsDictionary[componentId] : undefined;
    let initMappedHosts: Set<HostId> | undefined;
    if (componentId) {
      // if check mapping to component - get initMappedHosts by componentId
      initMappedHosts = initiallyMappedHosts[componentId];
    } else if (initiallyMappedComponents[host.id]?.size) {
      // alter case - we check absolute available of host:
      // we should check case, when host had mapped components but user local remove it
      // in this case we don't full block this host, and we create fake initMappedHosts with this hostId
      initMappedHosts = new Set([host.id]);
    }
    // const initMappedHosts = componentId ? initiallyMappedHosts[componentId] : undefined;
    return checkHostActionsUnmappingAvailability(host, allowActions, initMappedHosts);
  };

  const checkComponentMappingAvailability = (component: AdcmMappingComponent) => {
    const componentId = component.id;
    const allowActions = allowActionsDictionary[componentId];
    return checkComponentActionsMappingAvailability(component, allowActions);
  };

  return (
    <HostsMapping
      {...props}
      checkHostMappingAvailability={checkHostMappingAvailability}
      checkHostUnmappingAvailability={checkHostUnmappingAvailability}
      checkComponentMappingAvailability={checkComponentMappingAvailability}
    />
  );
};

export default ActionWizardHostsMapping;

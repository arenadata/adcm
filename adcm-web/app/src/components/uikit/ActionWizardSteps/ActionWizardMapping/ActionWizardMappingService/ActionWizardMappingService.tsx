import type { ServiceProps } from '@pages/cluster/ClusterMapping/ComponentsMapping/Service/Service';
import type {
  AdcmHostComponentMapRuleAction,
  AdcmHostShortView,
  AdcmMappingComponent,
  AdcmMappingComponentService,
} from '@models/adcm';
import cn from 'classnames';
import { useMemo } from 'react';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import Text from '@uikit/Text/Text';
import {
  checkComponentActionsMappingAvailability,
  checkHostActionsMappingAvailability,
  checkHostActionsUnmappingAvailability,
} from '@commonComponents/DynamicActionDialog/DynamicActionSteps/DynamicActionHostMapping/DynamicActionHostMapping.utils';
import ComponentContainer from '@pages/cluster/ClusterMapping/ComponentsMapping/ComponentContainer/ComponentContainer';
import s from './ActionWizardMappingService.module.scss';
import type { AdcmActionProcessMappingStepRules } from '@models/adcm/wizard';

const getComponentMapActions = (
  rules: { operation: AdcmHostComponentMapRuleAction; component: string; service: string }[],
  service: AdcmMappingComponentService,
  component: AdcmMappingComponent,
) => {
  const result = new Set<AdcmHostComponentMapRuleAction>();

  for (const rule of rules) {
    if (rule.service === service.name && rule.component === component.name) {
      result.add(rule.operation);
    }
  }

  return result;
};

interface ActionServiceProps extends Omit<ServiceProps, 'onInstallServices'> {
  rules: AdcmActionProcessMappingStepRules[];
  initiallyMappedHosts: Record<number, Set<number>>;
  onInstallServices?: (component: AdcmMappingComponent) => void;
  isReadOnly?: boolean;
}

const ActionWizardMappingService = ({
  service,
  componentsMapping,
  hasErrors,
  anchorId,
  hosts,
  mappingFilter,
  mappingErrors,
  onMap,
  onUnmap,
  onInstallServices,
  rules,
  initiallyMappedHosts,
  isReadOnly = false,
}: ActionServiceProps) => {
  const titleClassName = cn(s.service__title, {
    [s.service__title_error]: hasErrors,
  });

  const markerType = !hasErrors ? 'check' : 'alert';

  const filteredComponentsMapping = useMemo(() => {
    return componentsMapping.filter((componentMapping) =>
      componentMapping.component.displayName.toLowerCase().includes(mappingFilter.componentDisplayName.toLowerCase()),
    );
  }, [mappingFilter.componentDisplayName, componentsMapping]);

  return (
    <div key={service.id} className={s.service}>
      <Text className={titleClassName} variant="h2" id={anchorId}>
        {service.displayName}
        <MarkerIcon type={markerType} variant="square" size="medium" />
      </Text>
      {filteredComponentsMapping.map((componentMapping) => {
        const allowActions = getComponentMapActions(rules, service, componentMapping.component);
        const componentMappingErrors = mappingErrors[componentMapping.component.id];

        const checkComponentMappingAvailability = (component: AdcmMappingComponent) => {
          return checkComponentActionsMappingAvailability(component, allowActions);
        };

        const checkHostMappingAvailability = (host: AdcmHostShortView) => {
          return checkHostActionsMappingAvailability(
            host,
            allowActions,
            initiallyMappedHosts[componentMapping.component.id],
          );
        };

        const checkHostUnmappingAvailability = (host: AdcmHostShortView) => {
          return checkHostActionsUnmappingAvailability(
            host,
            allowActions,
            initiallyMappedHosts[componentMapping.component.id],
          );
        };

        return (
          <ComponentContainer
            key={componentMapping.component.id}
            componentMapping={componentMapping}
            mappingErrors={componentMappingErrors}
            filter={mappingFilter}
            allHosts={hosts}
            onMap={onMap}
            onUnmap={onUnmap}
            onInstallServices={onInstallServices}
            checkComponentMappingAvailability={checkComponentMappingAvailability}
            checkHostMappingAvailability={checkHostMappingAvailability}
            checkHostUnmappingAvailability={checkHostUnmappingAvailability}
            isReadOnly={isReadOnly}
          />
        );
      })}
    </div>
  );
};

export default ActionWizardMappingService;

import type { ServiceProps } from '@pages/cluster/ClusterMapping/ComponentsMapping/Service/Service';
import type { AdcmHostComponentMapRuleAction, AdcmHostShortView, AdcmMappingComponent } from '@models/adcm';
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
import type { ComponentAvailabilityErrors, ComponentMapping } from '@pages/cluster/ClusterMapping/ClusterMapping.types';

interface ActionServiceProps extends Omit<ServiceProps, 'onInstallServices' | 'componentsMapping'> {
  componentsMapping: (ComponentMapping & { allowedActions: Set<AdcmHostComponentMapRuleAction> })[];
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
        const component = componentMapping.component;
        const componentMappingErrors = mappingErrors[component.id];
        const allowActions = componentMapping.allowedActions;

        const checkWizardComponentMappingAvailability = (
          component: AdcmMappingComponent,
        ): ComponentAvailabilityErrors => {
          return checkComponentActionsMappingAvailability(component, allowActions);
        };

        const checkWizardHostMappingAvailability = (host: AdcmHostShortView): string | undefined => {
          return checkHostActionsMappingAvailability(host, allowActions, initiallyMappedHosts[component.id]);
        };

        const checkWizardHostUnmappingAvailability = (host: AdcmHostShortView): string | undefined => {
          return checkHostActionsUnmappingAvailability(host, allowActions, initiallyMappedHosts[component.id]);
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
            checkComponentMappingAvailability={checkWizardComponentMappingAvailability}
            checkHostMappingAvailability={checkWizardHostMappingAvailability}
            checkHostUnmappingAvailability={checkWizardHostUnmappingAvailability}
            isReadOnly={isReadOnly}
          />
        );
      })}
    </div>
  );
};

export default ActionWizardMappingService;

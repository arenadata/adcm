import { useMemo } from 'react';
import { Text, MarkerIcon } from '@uikit';
import ComponentContainer from '../ComponentContainer/ComponentContainer';
import type { ComponentsMappingErrors, MappingFilter, ComponentMapping } from '../../ClusterMapping.types';
import type { AdcmHostShortView, AdcmMappingComponent, AdcmMappingComponentService } from '@models/adcm';
import s from './Service.module.scss';
import cn from 'classnames';

export interface ServiceProps {
  service: AdcmMappingComponentService;
  componentsMapping: ComponentMapping[];
  anchorId: string;
  hosts: AdcmHostShortView[];
  mappingFilter: MappingFilter;
  mappingErrors: ComponentsMappingErrors;
  onMap: (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  onInstallServices?: (component: AdcmMappingComponent) => void;
}

const Service = ({
  service,
  componentsMapping,
  anchorId,
  hosts,
  mappingFilter,
  mappingErrors,
  onMap,
  onUnmap,
  onInstallServices,
}: ServiceProps) => {
  const isServiceValid = componentsMapping.every((cm) => mappingErrors[cm.component.id] === undefined);
  const titleClassName = cn(s.service__title, {
    [s.service__title_error]: !isServiceValid,
  });

  const markerType = isServiceValid ? 'check' : 'alert';

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
        return (
          <ComponentContainer
            key={componentMapping.component.id}
            componentMapping={componentMapping}
            mappingErrors={mappingErrors[componentMapping.component.id]}
            filter={mappingFilter}
            allHosts={hosts}
            onMap={onMap}
            onUnmap={onUnmap}
            onInstallServices={onInstallServices}
          />
        );
      })}
    </div>
  );
};

export default Service;

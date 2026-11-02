import { useMemo } from 'react';
import { Text, MarkerIcon } from '@uikit';
import ComponentContainerV2 from '../ComponentContainer/ComponentContainerV2';
import type { ComponentsMappingErrors, MappingFilter, ComponentMapping } from '../../ClusterMapping.types';
import type { AdcmHostShortView, AdcmMappingComponent, AdcmMappingComponentService } from '@models/adcm';
import type { ComponentHostRelations } from '@utils/mapping/mapping.types';
import s from './Service.module.scss';
import cn from 'classnames';

export interface ServiceV2Props {
  service: AdcmMappingComponentService;
  componentsMapping: ComponentMapping[];
  hasErrors?: boolean;
  anchorId: string;
  hosts: AdcmHostShortView[];
  mappingFilter: MappingFilter;
  mappingErrors: ComponentsMappingErrors;
  relations: ComponentHostRelations;
  onMap: (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  onInstallServices?: (component: AdcmMappingComponent) => void;
  isReadOnly?: boolean;
}

const ServiceV2 = ({
  service,
  componentsMapping,
  hasErrors,
  anchorId,
  hosts,
  mappingFilter,
  mappingErrors,
  relations,
  onMap,
  onUnmap,
  onInstallServices,
  isReadOnly = false,
}: ServiceV2Props) => {
  const titleClassName = cn(s.service__title, {
    [s.service__title_error]: hasErrors,
  });

  const markerType = !hasErrors ? 'check' : 'alert';

  const preparedComponentsMapping = useMemo(() => {
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
      {preparedComponentsMapping.map((componentMapping) => (
        <ComponentContainerV2
          key={componentMapping.component.id}
          componentMapping={componentMapping}
          mappingErrors={mappingErrors[componentMapping.component.id]}
          filter={mappingFilter}
          allHosts={hosts}
          relations={relations}
          onMap={onMap}
          onUnmap={onUnmap}
          onInstallServices={onInstallServices}
          isReadOnly={isReadOnly}
        />
      ))}
    </div>
  );
};

export default ServiceV2;

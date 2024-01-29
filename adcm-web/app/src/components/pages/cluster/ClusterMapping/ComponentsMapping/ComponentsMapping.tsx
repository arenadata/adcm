import { useMemo } from 'react';
import { AnchorBar, AnchorBarItem, AnchorList, MarkerIcon, Text } from '@uikit';
import ComponentContainer from './ComponentContainer/ComponentContainer';
import { Link, useParams } from 'react-router-dom';
import RequiredServicesDialog from '@pages/cluster/ClusterMapping/ComponentsMapping/RequiredServicesDialog/RequiredServicesDialog';
import { AdcmEntitySystemState, AdcmHostShortView, AdcmMaintenanceMode, AdcmMappingComponent } from '@models/adcm';
import { MappingFilter, MappingValidation, ServiceMapping } from '../ClusterMapping.types';
import s from './ComponentsMapping.module.scss';
import cn from 'classnames';
import { NotAddedServicesDictionary } from '@store/adcm/cluster/mapping/mappingSlice';

const buildServiceAnchorId = (id: number) => `anchor_${id}`;

export interface ComponentsMappingProps {
  hosts: AdcmHostShortView[];
  servicesMapping: ServiceMapping[];
  mappingValidation: MappingValidation;
  mappingFilter: MappingFilter;
  notAddedServicesDictionary: NotAddedServicesDictionary;
  onMap: (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => void;
  onUnmap: (hostId: number, componentId: number) => void;
}

const ComponentsMapping = ({
  hosts,
  servicesMapping,
  mappingValidation,
  mappingFilter,
  notAddedServicesDictionary,
  onMap,
  onUnmap,
}: ComponentsMappingProps) => {
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const anchorItems: AnchorBarItem[] = useMemo(
    () =>
      servicesMapping.map((m) => ({
        label: m.service.displayName,
        id: buildServiceAnchorId(m.service.id),
      })),
    [servicesMapping],
  );

  return (
    <div className={s.componentsMapping}>
      <div data-test="mapping-container">
        {servicesMapping.map(({ service, componentsMapping }) => {
          const isServiceValid = componentsMapping.every(
            (cm) => mappingValidation.byComponents[cm.component.id].isValid,
          );
          const titleClassName = cn(s.serviceMapping__title, {
            [s['serviceMapping__title_error']]: !isServiceValid,
          });

          const markerType = isServiceValid ? 'check' : 'alert';

          return (
            <div key={service.id} className={s.serviceMapping}>
              <Text className={titleClassName} variant="h2" id={buildServiceAnchorId(service.id)}>
                {service.displayName}
                <MarkerIcon type={markerType} variant="square" size="medium" />
              </Text>
              {componentsMapping.map((componentMapping) => {
                const isEditableComponent =
                  componentMapping.component.service.state === AdcmEntitySystemState.Created &&
                  componentMapping.component.maintenanceMode !== AdcmMaintenanceMode.On;

                return (
                  <ComponentContainer
                    key={componentMapping.component.id}
                    componentMapping={componentMapping}
                    componentMappingValidation={mappingValidation.byComponents[componentMapping.component.id]}
                    filter={mappingFilter}
                    allHosts={hosts}
                    notAddedServicesDictionary={notAddedServicesDictionary}
                    onMap={onMap}
                    onUnmap={onUnmap}
                    allowActions={isEditableComponent ? undefined : []}
                  />
                );
              })}
            </div>
          );
        })}
        {servicesMapping.length === 0 && (
          <div>
            Add services on the{' '}
            <Link className="text-link" to={`/clusters/${clusterId}/services`}>
              services page
            </Link>
          </div>
        )}
      </div>
      <AnchorBar>
        <AnchorList items={anchorItems} />
      </AnchorBar>

      <RequiredServicesDialog />
    </div>
  );
};

export default ComponentsMapping;

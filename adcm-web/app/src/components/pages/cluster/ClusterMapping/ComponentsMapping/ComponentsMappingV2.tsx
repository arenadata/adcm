import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { AnchorBarItem } from '@uikit';
import { AnchorBar, AnchorList } from '@uikit';
import ServiceV2 from './Service/ServiceV2';
import type { AdcmHostShortView, AdcmMappingComponent } from '@models/adcm';
import type { MappingFilter, ComponentsMappingErrors, ServiceMapping } from '../ClusterMapping.types';
import type { ComponentHostRelations } from '@utils/mapping/mapping.types';
import s from './ComponentsMapping.module.scss';

const buildServiceAnchorId = (id: number) => `anchor_${id}`;

export interface ComponentsMappingV2Props {
  hosts: AdcmHostShortView[];
  servicesMapping: ServiceMapping[];
  mappingErrors: ComponentsMappingErrors;
  mappingFilter: MappingFilter;
  relations: ComponentHostRelations;
  onMap: (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  onInstallServices: (component: AdcmMappingComponent) => void;
}

const ComponentsMappingV2 = ({ servicesMapping, ...restProps }: ComponentsMappingV2Props) => {
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
        {servicesMapping.map(({ service, componentsMapping, hasErrors }) => (
          <ServiceV2
            key={service.id}
            service={service}
            componentsMapping={componentsMapping}
            hasErrors={hasErrors}
            anchorId={buildServiceAnchorId(service.id)}
            {...restProps}
          />
        ))}
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
    </div>
  );
};

export default ComponentsMappingV2;

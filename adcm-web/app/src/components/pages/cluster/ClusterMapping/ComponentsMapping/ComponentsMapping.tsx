import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AnchorBar, AnchorBarItem, AnchorList } from '@uikit';
import Service from './Service/Service';
import { AdcmHostShortView, AdcmMappingComponent } from '@models/adcm';
import type { MappingFilter, ComponentsMappingErrors, ServiceMapping } from '../ClusterMapping.types';
import s from './ComponentsMapping.module.scss';

const buildServiceAnchorId = (id: number) => `anchor_${id}`;

export interface ComponentsMappingProps {
  hosts: AdcmHostShortView[];
  servicesMapping: ServiceMapping[];
  mappingErrors: ComponentsMappingErrors;
  mappingFilter: MappingFilter;
  onMap: (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  onInstallServices: (component: AdcmMappingComponent) => void;
}

const ComponentsMapping = ({ servicesMapping, ...restProps }: ComponentsMappingProps) => {
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
        {servicesMapping.map(({ service, componentsMapping }) => (
          <Service
            service={service}
            componentsMapping={componentsMapping}
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

export default ComponentsMapping;

import HostContainer from './HostContainer/HostContainer';
import { useDispatch, useStore } from '@hooks';
import { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { HostMapping, MappingFilter, MappingValidation } from '../ClusterMapping.types';
import s from './HostsMapping.module.scss';

export interface HostsMappingProps {
  hostsMapping: HostMapping[];
  mappingValidation: MappingValidation;
  mappingFilter: MappingFilter;
}

const HostsMapping = ({ hostsMapping, mappingValidation, mappingFilter }: HostsMappingProps) => {
  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Mapping' },
          { label: 'Hosts view' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <div className={s.hostsMapping}>
      {hostsMapping.map((hostMapping) => (
        <HostContainer
          key={hostMapping.host.id}
          hostMapping={hostMapping}
          mappingValidation={mappingValidation}
          filter={mappingFilter}
          className={s.hostContainer}
        />
      ))}
    </div>
  );
};

export default HostsMapping;
